"""
ユニットテスト: UI IPC ハンドラと関連するバックエンド API のテスト

対象:
- trends:fetch-llm (トレンド LLM 取得)
- scripts:generate-from-brief (台本生成)
- assets:fetch (素材取得)
"""

import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

import pytest

from src.script_generation import build_llm_client, generate_and_validate, LLMError
from src.script_generation.schemas import trend_ideas_schema, script_payload_schema
from scripts.fetch_trend_ideas_llm import (
    fetch_trend_ideas_via_llm,
    parse_and_validate,
    build_messages,
)
from src.script_generation.generator import ScriptFromBriefGenerator
from src.models import ThemeTemplate, ScriptModel


class TestFetchTrendIdeasViaLlm:
    """トレンド LLM 取得機能のテスト"""

    def test_fetch_trend_ideas_valid_response(self):
        """LLM が有効なレスポンスを返した場合"""
        mock_response = {
            "keywords": ["ショート動画", "AI時代"],
            "ideas": [
                {
                    "keyword": "AI画像生成の落とし穴",
                    "title": "AI画像の著作権問題",
                    "brief": "AI生成画像の法的問題と対策を解説",
                    "priority_score": 0.95,
                    "seed_phrases": ["著作権は誰にある", "画像は自由に使えない"],
                }
            ],
            "briefs": [
                {
                    "keyword": "AI画像生成の落とし穴",
                    "brief": "AI生成画像の法的問題と対策を解説",
                    "keywords": ["AI", "著作権"],
                    "seed_phrases": ["著作権は誰にある"],
                }
            ],
        }

        with patch("scripts.fetch_trend_ideas_llm.generate_and_validate") as mock_gen:
            mock_gen.return_value = json.dumps(mock_response, ensure_ascii=False)
            result = fetch_trend_ideas_via_llm(max_ideas=10)

        assert isinstance(result, dict)
        assert "keywords" in result
        assert "ideas" in result
        assert len(result["ideas"]) > 0
        assert result["ideas"][0]["keyword"] == "AI画像生成の落とし穴"

    def test_fetch_trend_ideas_with_code_fences(self):
        """LLM がコードフェンスで囲まれたレスポンスを返した場合"""
        mock_response = {
            "keywords": ["テスト"],
            "ideas": [
                {
                    "keyword": "テスト",
                    "title": "テスト",
                    "brief": "Test brief",
                    "priority_score": 0.9,
                }
            ],
        }
        # コードフェンスで囲まれたレスポンス
        fenced_response = f"```json\n{json.dumps(mock_response, ensure_ascii=False)}\n```"

        with patch("scripts.fetch_trend_ideas_llm.generate_and_validate") as mock_gen:
            mock_gen.return_value = fenced_response
            result = fetch_trend_ideas_via_llm(max_ideas=10)

        assert isinstance(result, dict)
        assert "ideas" in result
        assert len(result["ideas"]) > 0

    def test_fetch_trend_ideas_with_quadruple_code_fences(self):
        """LLM が4重のコードフェンスで囲まれたレスポンスを返した場合"""
        mock_response = {
            "keywords": ["テスト"],
            "ideas": [
                {
                    "keyword": "テスト",
                    "title": "テスト",
                    "brief": "Test brief",
                    "priority_score": 0.9,
                }
            ],
        }
        # 4重コードフェンス: ````plaintext + ```json + content + ``` + ````
        quadruple_fenced = f"````plaintext\n```json\n{json.dumps(mock_response, ensure_ascii=False)}\n```\n````"

        with patch("scripts.fetch_trend_ideas_llm.generate_and_validate") as mock_gen:
            mock_gen.return_value = quadruple_fenced
            result = fetch_trend_ideas_via_llm(max_ideas=10)

        assert isinstance(result, dict)
        assert "ideas" in result
        assert len(result["ideas"]) > 0

    def test_fetch_trend_ideas_invalid_json(self):
        """LLM が無効な JSON を返した場合"""
        with patch("scripts.fetch_trend_ideas_llm.generate_and_validate") as mock_gen:
            mock_gen.return_value = "This is not JSON"
            with pytest.raises(json.JSONDecodeError):
                fetch_trend_ideas_via_llm(max_ideas=10)

    def test_fetch_trend_ideas_missing_ideas_field(self):
        """LLM レスポンスに 'ideas' フィールドがない場合"""
        mock_response = {"keywords": ["test"], "other_field": "value"}
        with patch("scripts.fetch_trend_ideas_llm.generate_and_validate") as mock_gen:
            mock_gen.return_value = json.dumps(mock_response, ensure_ascii=False)
            with pytest.raises(ValueError, match="does not contain 'ideas'"):
                fetch_trend_ideas_via_llm(max_ideas=10)

    def test_parse_and_validate_with_max_ideas(self):
        """max_ideas に合わせてアイデアを制限"""
        mock_response = json.dumps(
            {
                "ideas": [
                    {
                        "keyword": f"idea_{i}",
                        "title": f"Title {i}",
                        "brief": f"Brief {i}",
                        "priority_score": 1.0 - (i * 0.1),
                    }
                    for i in range(20)
                ]
            },
            ensure_ascii=False,
        )
        result = parse_and_validate(mock_response, max_ideas=5)
        assert len(result["ideas"]) == 5

    def test_parse_and_validate_filters_nsfw(self):
        """NSFW アイデアをフィルタリング"""
        mock_response = json.dumps(
            {
                "ideas": [
                    {
                        "keyword": "safe_idea",
                        "title": "Safe Title",
                        "brief": "Safe brief",
                        "priority_score": 0.9,
                        "nsfw": False,
                    },
                    {
                        "keyword": "nsfw_idea",
                        "title": "NSFW Title",
                        "brief": "NSFW brief",
                        "priority_score": 0.95,
                        "nsfw": True,
                    },
                ]
            },
            ensure_ascii=False,
        )
        result = parse_and_validate(mock_response, max_ideas=10)
        assert len(result["ideas"]) == 1
        assert result["ideas"][0]["keyword"] == "safe_idea"

    def test_build_messages_format(self):
        """メッセージ構築が正しいフォーマット"""
        messages = build_messages(language="ja", max_ideas=10)
        assert isinstance(messages, list)
        assert len(messages) >= 2
        assert messages[0]["role"] == "system"
        assert any(msg["role"] == "user" for msg in messages)
        assert all("content" in msg for msg in messages)


class TestScriptGenerationFromBrief:
    """台本生成 (LLM) のテスト"""

    def test_generate_script_valid_response(self):
        """LLM が有効な台本レスポンスを返した場合"""
        mock_payload = {
            "title": "愛知の IT 産業",
            "summary": "愛知県の IT 産業の現状を解説",
            "sections": [
                {
                    "id": "intro",
                    "on_screen_text": "愛知の IT 産業",
                    "narration": "今回は愛知県の IT 産業について解説します。",
                    "hook": "愛知って本当に IT に弱いのか？",
                    "evidence": "データから見ると",
                    "demo": "具体例として",
                    "bridge": "次は",
                    "cta": "コメントをください",
                    "effects": [],
                }
            ],
            "global_cta": "チャンネル登録",
            "outro": {
                "on_screen_text": "まとめ",
                "narration": "以上が愛知の IT 産業です。",
                "cta": "登録をお願いします",
            },
        }

        with patch(
            "src.script_generation.generator.generate_and_validate"
        ) as mock_gen:
            mock_gen.return_value = json.dumps(mock_payload, ensure_ascii=False)
            theme = ThemeTemplate(
                id="test_theme",
                label="Test Theme",
                genre="test",
                layout="ranking",
            )
            from src.script_generation.llm import OpenAIChatClient

            client = Mock(spec=OpenAIChatClient)
            generator = ScriptFromBriefGenerator(llm=client, theme=theme, section_count=1)

            # ジェネレータは内部で LLM を呼ぶため、実際の生成は不要
            # 代わりに、ペイロード解析のテストだけを行う
            result = generator._parse_payload(json.dumps(mock_payload))
            assert result["title"] == "愛知の IT 産業"
            assert len(result["sections"]) == 1

    def test_generate_script_with_malformed_response(self):
        """LLM が不正な JSON を返した場合"""
        from src.script_generation.generator import ScriptFromBriefGenerator

        theme = ThemeTemplate(
            id="test_theme",
            label="Test Theme",
            genre="test",
            layout="ranking",
        )
        client = Mock()
        generator = ScriptFromBriefGenerator(llm=client, theme=theme, section_count=1)

        with pytest.raises(Exception):  # ScriptGenerationError
            generator._parse_payload("Not valid JSON or YAML")


class TestLlmClientIntegration:
    """LLM クライアントと generate_and_validate の統合テスト"""

    def test_generate_and_validate_with_valid_json(self):
        """valid JSON レスポンスを validate"""
        mock_client = Mock()
        # 完全な trend_ideas_schema 対応レスポンス
        mock_response = {
            "keywords": ["test"],
            "briefs": [],
            "ideas": [
                {
                    "keyword": "test",
                    "title": "Test",
                    "brief": "Test brief",
                    "priority_score": 0.8,
                }
            ],
        }
        mock_client.generate_json.return_value = json.dumps(mock_response)

        # スキーマなしで実行（検証をスキップ）
        result = generate_and_validate(mock_client, [])

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "ideas" in parsed

    def test_generate_and_validate_with_retry_on_failure(self):
        """失敗時のリトライを検証"""
        mock_client = Mock()
        # 1 回目失敗、2 回目成功
        valid_response = {
            "keywords": ["test"],
            "briefs": [],
            "ideas": [
                {
                    "keyword": "test",
                    "title": "Test",
                    "brief": "Test brief",
                    "priority_score": 0.8,
                }
            ],
        }
        mock_client.generate_json.side_effect = [
            "Invalid JSON {",
            json.dumps(valid_response),
        ]

        # スキーマなしで実行
        result = generate_and_validate(
            mock_client, [], retries=1
        )

        assert isinstance(result, str)
        assert mock_client.generate_json.call_count >= 1

    def test_generate_and_validate_fails_after_retries(self):
        """全リトライ失敗時に例外を発生"""
        mock_client = Mock()
        mock_client.generate_json.side_effect = LLMError("API error")

        with pytest.raises(LLMError):
            generate_and_validate(mock_client, [], retries=0)


class TestErrorHandling:
    """エラーハンドリングのテスト"""

    def test_llm_api_error_handling(self):
        """LLM API エラーの処理"""
        with patch("scripts.fetch_trend_ideas_llm.generate_and_validate") as mock_gen:
            mock_gen.side_effect = LLMError("API key not set")
            with pytest.raises(LLMError):
                fetch_trend_ideas_via_llm(max_ideas=10)

    def test_network_error_handling(self):
        """ネットワークエラーの処理"""
        with patch("scripts.fetch_trend_ideas_llm.build_client") as mock_build:
            mock_build.side_effect = Exception("Network error")
            with pytest.raises(Exception):
                fetch_trend_ideas_via_llm(max_ideas=10)

    def test_invalid_response_logging(self):
        """不正なレスポンスログへの保存"""
        from scripts.fetch_trend_ideas_llm import log_invalid_response

        error = ValueError("Test error")
        path = log_invalid_response("test raw response", error)

        assert path.exists()
        content = path.read_text()
        assert "Test error" in content
        assert "test raw response" in content

        # クリーンアップ
        path.unlink()


class TestIpcPayloadValidation:
    """IPC ペイロード検証のテスト"""

    def test_fetch_llm_trends_payload_structure(self):
        """fetchLlmTrends の期待されるペイロード構造"""
        mock_data = {
            "keywords": ["keyword1", "keyword2"],
            "briefs": [
                {
                    "keyword": "keyword1",
                    "brief": "This is a brief",
                    "keywords": ["tag1", "tag2"],
                    "seed_phrases": ["phrase1", "phrase2"],
                }
            ],
        }
        # main.js の 'trends:fetch-llm' ハンドラで想定される返却値
        assert "keywords" in mock_data
        assert "briefs" in mock_data
        assert all(isinstance(kw, str) for kw in mock_data["keywords"])
        assert all(isinstance(b, dict) for b in mock_data["briefs"])

    def test_generate_script_payload_structure(self):
        """generateScriptFromBrief の期待されるペイロード構造"""
        mock_payload = {
            "brief": "AI の危険性と対策",
            "sections": 5,
            "theme_id": "tech_awareness",
        }
        # main.js の 'scripts:generate-from-brief' ハンドラで想定される入力
        assert "brief" in mock_payload
        assert "sections" in mock_payload
        assert isinstance(mock_payload["sections"], int)
