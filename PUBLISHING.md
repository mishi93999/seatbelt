# How to publish Seatbelt — step by step
## (Explained like you've never done this before)

Publishing a Python library is a two-part job:
- **GitHub**: where your code lives, where people collaborate
- **PyPI**: the "app store" where people download your library via `pip install seatbelt`

---

## Part 1: GitHub (where your code lives)

### Step 1: Create a GitHub account (if you don't have one)
Go to https://github.com and sign up. Free.

### Step 2: Create a new repository
1. Click the **+** button in the top-right → **New repository**
2. Repository name: `seatbelt`
3. Description: `Responsible AI auditing for LLMs and SLMs`
4. Set to **Public** (required for open source)
5. Check "Add a README" — **don't do this** (we already have one)
6. Click **Create repository**

### Step 3: Push your code to GitHub
On your computer, in the `seatbelt/` folder:

```bash
# Initialize git (do this once)
git init
git add .
git commit -m "Initial release: Seatbelt v0.1.0"

# Connect to GitHub (replace 'yourusername' with your GitHub handle)
git remote add origin https://github.com/yourusername/seatbelt.git
git branch -M main
git push -u origin main
```

### Step 4: Add topics to your GitHub repo
On your repo page, click the gear icon next to "About", then add these topics:
```
responsible-ai  llm  ai-safety  fairness  bias-detection
sycophancy  eu-ai-act  ai-audit  machine-learning  nlp
```
Topics are how people FIND your repo on GitHub. This is important for stars.

### Step 5: Create a GitHub Release (tagging v0.1.0)
1. On your repo page, click **Releases** (right sidebar)
2. Click **Create a new release**
3. Tag: `v0.1.0`
4. Title: `Seatbelt v0.1.0 — Initial release`
5. Describe what's in this release (copy from the README roadmap section)
6. Click **Publish release**

This creates an official snapshot of your code at this version.

---

## Part 2: PyPI (where `pip install seatbelt` comes from)

### Step 1: Create a PyPI account
Go to https://pypi.org and sign up. Free.
Enable 2-factor authentication (required).

### Step 2: Install the build tools (one time)
```bash
pip install build twine
```

- `build` turns your code into a "package" file
- `twine` uploads that package to PyPI

### Step 3: Build the package
Inside your `seatbelt/` folder:

```bash
python -m build
```

This creates a `dist/` folder containing two files:
- `seatbelt-0.1.0.tar.gz` — the source distribution
- `seatbelt-0.1.0-py3-none-any.whl` — the wheel (faster install)

### Step 4: Test on TestPyPI first (important!)
TestPyPI is a sandbox — you can publish there for free to make sure everything works
before publishing to the real PyPI.

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Test install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ seatbelt
```

### Step 5: Publish to the real PyPI
```bash
twine upload dist/*
```

It will ask for your PyPI username and password (or API token — use the token).

After this, anyone in the world can run:
```bash
pip install seatbelt
```

### Step 6: Get an API token (recommended over password)
1. Go to https://pypi.org/manage/account/token/
2. Create a token scoped to the `seatbelt` project
3. Use it instead of your password in twine

---

## Part 3: How to release future versions

When you make changes and want to release v0.2.0:

1. Update the version in `pyproject.toml`: `version = "0.2.0"`
2. Commit and push: `git add . && git commit -m "Release v0.2.0" && git push`
3. Tag the release: `git tag v0.2.0 && git push --tags`
4. Build: `python -m build`
5. Upload: `twine upload dist/*`

---

## Part 4: Getting GitHub stars and forks

Stars on GitHub = people bookmarking your project. They're like a credibility score.
Forks = people making a copy to contribute to. High forks = active community.

### How to get your first 100 stars:

1. **Post on Hacker News** (https://news.ycombinator.com/submit)
   Title format: "Show HN: Seatbelt – Responsible AI auditing for LLMs (open source)"
   Post on a weekday morning EST. This alone can get you 200-500+ stars.

2. **Post on Reddit**:
   - r/MachineLearning
   - r/artificial
   - r/LocalLLaMA (for the SLM angle)
   - r/programming

3. **Tweet/post on X and LinkedIn**:
   Show the output. The scorecard screenshot is your best marketing.
   People share things that look like useful tools.

4. **Post on Hugging Face** community forums — lots of ML practitioners there.

5. **Write a blog post** explaining why you built it and what problem it solves.
   Post on Medium or your own blog. Link to the GitHub repo from everywhere.

6. **Add a "Used by" section** to your README as companies adopt it.

7. **Respond to every GitHub Issue** in the first month.
   Early adopters become advocates if you treat them well.

### What makes a repo get forked:
- Clean, readable code with lots of comments (✅ Seatbelt has this)
- Easy to contribute (each agent is isolated in its own file)
- A clear roadmap of what's coming
- Issues labeled "good first issue" for beginners

---

## Part 5: Setting up CI/CD (automatic testing)

Create `.github/workflows/test.yml` to automatically run tests on every push:

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: pytest tests/ -v
```

This shows a green ✅ badge on your README, which makes people trust your library.

---

## Summary: The full publishing checklist

- [ ] Create GitHub account
- [ ] Create `seatbelt` repo (public)
- [ ] Push code to GitHub
- [ ] Add topics to the repo
- [ ] Create a v0.1.0 release on GitHub
- [ ] Create PyPI account + enable 2FA
- [ ] `pip install build twine`
- [ ] `python -m build`
- [ ] `twine upload --repository testpypi dist/*` (test first)
- [ ] `twine upload dist/*` (publish for real)
- [ ] Post on Hacker News (Show HN)
- [ ] Post on Reddit (r/MachineLearning, r/LocalLLaMA)
- [ ] Set up GitHub Actions for CI

Total time from code to published: about 30 minutes.
