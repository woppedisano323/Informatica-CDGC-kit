# Quick Start — Informatica CDGC Kit

This guide is for people who have never used Terminal or Python before. Follow each step exactly as written.

---

## Step 1 — Open Terminal

Terminal is an app on your Mac that lets you type commands directly to your computer.

1. Press **Cmd + Space** on your keyboard
2. Type `Terminal`
3. Press **Enter**

A window opens with a blinking cursor. This is your Terminal. You type commands here and press Enter to run them.

---

## Step 2 — Install Claude Code

Claude Code is the AI assistant that powers the skills in this kit.

In Terminal, type this and press Enter:
```
npm install -g @anthropic-ai/claude-code
```

> If you see `command not found: npm`, you need to install Node.js first. Go to nodejs.org, download the installer, run it, then come back and try again.

---

## Step 3 — Get the repo (download the kit)

In Terminal, type these commands one at a time, pressing Enter after each:

```
cd ~
git clone https://github.com/woppedisano323/Informatica-CDGC-kit.git
cd Informatica-CDGC-kit
```

**What this does:** Downloads all the files from GitHub to your computer into a folder called `Informatica-CDGC-kit` in your home directory.

---

## Step 4 — Install Python dependencies (one time only)

The Python scripts in this kit need a few extra libraries. Install them by typing:

```
pip install openpyxl pdfplumber python-docx requests flask
```

Press Enter and wait for it to finish. You should see a line saying `Successfully installed...` at the end.

> If you see `command not found: pip`, try `pip3` instead of `pip`.

---

## Step 5 — Open Claude Code

Still in Terminal, type:
```
claude .
```

Press Enter. Claude Code will open and automatically load all the skills from this repo.

---

## Step 6 — Use a skill

In the Claude Code prompt, type one of these and press Enter:

| Type this | To do this |
|-----------|-----------|
| `/cdgc-setup` | Build a demo CDGC org for any industry |
| `/cdgc-client-setup` | Build a CDGC org from your client's documents |
| `/cdgc-wipe` | Clear all assets from a demo org |

Claude will guide you through the rest with questions.

---

## Running the live dashboard

The dashboard opens a live browser view of your CDGC org.

1. Open Terminal (or open a new Terminal tab with **Cmd + T**)
2. Type this and press Enter:
```
cd ~/Informatica-CDGC-kit
python3 .claude/commands/cdgc_dashboard.py
```
3. Enter your IDMC username (your Informatica Cloud email) when asked
4. Enter your IDMC password when asked (you won't see it as you type — that's normal)
5. A browser window opens automatically at `http://localhost:8080`

To stop the dashboard, go back to Terminal and press **Ctrl + C**.

---

## Running the API import script

Use this after `/cdgc-setup` or `/cdgc-client-setup` has generated your Excel files, if you prefer not to upload them manually in the CDGC UI.

1. Open Terminal
2. Type this and press Enter:
```
cd ~/Informatica-CDGC-kit
python3 .claude/commands/cdgc_api_import.py
```
3. Enter your IDMC username and password when asked
4. The script uploads all 14 files in order and shows progress

---

## Checking what's in your CDGC org

To see a count of all asset types currently in your org:

```
cd ~/Informatica-CDGC-kit
python3 .claude/commands/cdgc_discover_classtypes.py
```

---

## Common issues

**"command not found: python3"**
Download Python from python.org, install it, then try again.

**"No module named 'flask'"**
Run `pip install openpyxl pdfplumber python-docx requests flask` again.

**"401 Unauthorized"**
Your IDMC username or password is wrong. Check for typos — the username is usually your email address.

**"Port 8080 already in use"**
Another program is using that port. Stop the other program, or close and reopen Terminal.

**Skills not loading in Claude Code**
Make sure you ran `claude .` from inside the `Informatica-CDGC-kit` folder, not from your home directory.

---

## Glossary of terms used in this kit

| Term | What it means |
|------|--------------|
| Terminal | The command-line app on your Mac |
| `cd` | Change directory — moves you into a folder |
| `python3` | Runs a Python script |
| `pip install` | Installs a Python library |
| IDMC | Informatica Cloud — the platform that hosts CDGC |
| CDGC | Cloud Data Governance & Catalog — the product this kit automates |
| Skill | A Claude Code command that starts with `/` |
| Import file | An Excel file formatted for CDGC bulk import |
