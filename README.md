# PTCL Spin The Wheel — Automation

Automatically plays the PTCL Spin the Wheel game on a daily schedule using
GitHub Actions. Free to run, no paid APIs needed.

## How it works

1. GitHub Actions triggers daily at 9 AM Pakistan time
2. Playwright opens a headless Chromium browser
3. Fills in your PTCL number and solves the CAPTCHA using `ddddocr` (free, offline ML)
4. Clicks spin, waits for the animation, extracts the result
5. Saves results to `spin_results.csv` and screenshots as downloadable artifacts

---

## Setup (one time, ~5 minutes)

### 1. Fork / create the repo

Create a new **private** GitHub repository and upload these files:

```
ptcl_spin_automation.py
requirements.txt
.github/
  workflows/
    spin.yml
```

### 2. Add your PTCL number as a Secret

GitHub keeps secrets encrypted — your number is never visible in logs.

1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `PTCL_NUMBER`
4. Value: your PTCL landline number (e.g. `0515551234`)
5. Click **Add secret**

### 3. Enable Actions

Go to the **Actions** tab of your repo and click **"I understand my workflows, go ahead and enable them"** if prompted.

### 4. Test it manually

Actions tab → **PTCL Spin The Wheel** → **Run workflow** → set spin count → **Run workflow**

Watch the live logs. After it finishes, download the artifacts (screenshots + CSV) from the run summary page.

---

## Schedule

The workflow runs daily at **9:00 AM PKT** (4:00 AM UTC).

To change the time, edit `.github/workflows/spin.yml` and update the cron line:

```yaml
- cron: "0 4 * * *"   # 4:00 AM UTC = 9:00 AM PKT
```

Use https://crontab.guru to figure out the UTC equivalent of your preferred time.

---

## Outputs

After each run you can download from the **Actions** run summary:

| Artifact | Contents | Kept for |
|---|---|---|
| `spin-screenshots-N` | CAPTCHA + result PNGs for each spin | 7 days |
| `spin-results-N` | CSV with spin number, timestamp, result | 30 days |

---

## Troubleshooting

**Login keeps failing?**
- Download the `captcha_spinX.png` screenshot from artifacts and check if the CAPTCHA was read correctly
- The PTCL site may have changed its HTML — check the element IDs and update the selectors in `ptcl_spin_automation.py`

**"Result not detected" in CSV?**
- Download `result_spinX.png` to see what the page looked like after spinning
- The result element ID may differ — inspect the page and update the `result_selectors` list in the script

**How to update selectors:**
Right-click the element in browser → Inspect → note the `id` or `name` attribute → add it to the relevant selector list in the script.

---

## Files

```
ptcl_spin_automation.py   # main script
requirements.txt          # python dependencies
.github/workflows/spin.yml  # GitHub Actions workflow
README.md                 # this file
```
