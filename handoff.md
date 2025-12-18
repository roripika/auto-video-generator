Hand‑off Document: Automated Step‑by‑Step
Documentation
Purpose
This document outlines the steps required to set up and operate an automated step‑by‑step
documentation generator for capturing GUI workflows as reproducible guides. The toolchain uses
Playwright to automate user interactions, capture screenshots and logs, and subsequently leverage an
LLM to convert the captured data into a polished markdown guide.
Background
Manual creation of step‑by‑step instructions is time‑consuming and prone to omission. To reduce this
overhead, we can automate the capture of user interactions. Playwright provides a robust browser
automation framework capable of recording sequences of user actions, capturing screenshots at each
step, and outputting structured logs. These logs can be processed by an LLM to generate coherent
explanations and formatted documentation.
Overview of Workflow
Setup Playwright: Install Playwright and its dependencies. Use Playwright to launch a browser
session and execute the target workflow.
Instrument Step Recording: Implement a StepRecorder class that captures a screenshot and
logs relevant metadata (URL, page title, action type, target selector, and annotations) after each
significant user action.
Define the Workflow: Write an automation script that replicates the user actions in sequence.
After each user interaction, invoke the recorder to capture the state.
Persist Data: Save the screenshots and logs (e.g., in JSON format) to a designated folder under
your project (e.g., docs/howto or docs/stepdocs ).
Generate Documentation: Pass the logs and screenshots to an LLM (e.g., via a separate script or
pipeline) to generate a markdown guide. The LLM can interpret the actions and provide
human‑readable descriptions for each step.
Review and Edit: Review the generated document for accuracy. Make any necessary edits
manually to ensure clarity and correctness.
Implementation Details
Playwright Installation
Initialize a Node.js project and install Playwright:
npm init -y
npm install -D playwright
npx playwright install
1.
2.
3.
4.
5.
6.
•
1
StepRecorder Class
Implement a reusable StepRecorder class in your Playwright script. The recorder should:
Increment a step counter.
Capture a full‑page screenshot after each step with a consistent naming scheme (e.g.,
step01.png , step02.png ).
Capture metadata: timestamp, URL, page title, action type (e.g., click, fill), target selector, custom
annotations.
Append the metadata to an array of steps.
Write the metadata array to a JSON file when the script finishes.
Example Script
Below is a minimal example that demonstrates how to capture a workflow on a website using Playwright
and the StepRecorder class:
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';
const OUT_DIR = path.resolve('docs/stepdocs');
const SHOT_DIR = path.join(OUT_DIR, 'screenshots');
const STEPS_JSON = path.join(OUT_DIR, 'steps.json');
function ensureDir(p) {
fs.mkdirSync(p, { recursive: true });
}
class StepRecorder {
constructor(page) {
this.page = page;
this.steps = [];
this.stepNo = 0;
}
async snap({ action, target, note }) {
this.stepNo += 1;
const id = String(this.stepNo).padStart(2, '0');
const file = `step${id}.png`;
const relPath = `screenshots/${file}`;
const absPath = path.join(SHOT_DIR, file);
await this.page.screenshot({ path: absPath, fullPage: true });
const url = this.page.url();
const title = await this.page.title().catch(() => '');
this.steps.push({ id: this.stepNo, url, title, action, target, note, screenshot: relPath });
}
save() {
ensureDir(OUT_DIR);
ensureDir(SHOT_DIR);
fs.writeFileSync(STEPS_JSON, JSON.stringify({ steps: this.steps }, null, 2), 'utf‑8');
}
•
•
•
•
•
2
}
(async () => {
const browser = await chromium.launch();
const page = await browser.newPage();
const recorder = new StepRecorder(page);
// Step 1: Navigate to example.com
await page.goto('https://example.com');
await recorder.snap({ action: 'goto', target: 'https://example.com', note: 'Open Example home
page' });
// Step 2: Click the 'More information' link
await page.click('text=More information');
await recorder.snap({ action: 'click', target: 'text=More information', note: 'Click More information
link' });
recorder.save();
await browser.close();
})();
Document Generation
After executing the script, you will have:
A folder screenshots/ containing images of each step.
A steps.json file listing each step’s metadata.
You can then design a separate script to convert steps.json plus the images into a markdown guide.
The conversion might use an LLM via its API. You should craft prompts that instruct the LLM to interpret
each step, write a human‑friendly description, and embed the corresponding screenshot.
Suggested Prompt for LLM
Provide the LLM with the JSON data and ask it to generate a structured markdown guide:
"Given the following step data (actions, targets, notes, screenshot file names), write a
detailed step‑by‑step guide. Each step should include a heading with the action
description and embed the corresponding image file (in markdown). Use the note field as
the basis for the description."
File Organization
A typical generated guide might reside in docs/stepdocs/guide.md and could look like:
# Guide: Example Website Walkthrough
## Step 1: Open Example home page
![Step 1](screenshots/step01.png)
•
•
3
Navigate to https://example.com to load the Example home page.
## Step 2: Click the 'More information' link
![Step 2](screenshots/step02.png)
On the home page, click the **More information** link to access additional details.
Next Steps
Expand the automation script to cover your full workflow.
Enhance the recorder to capture additional context (e.g., input values for form fields, page text
excerpts).
Build error handling into the script to manage unexpected dialogs or navigation errors.
Automate the LLM call and guide generation as part of a CI pipeline, if desired.
Conclusion
By following this hand‑off document, you can set up an automated system for generating detailed step‑
by‑step documentation. This not only improves documentation consistency but also reduces the manual
effort required to create instructional materials.
•
•
•
•
4