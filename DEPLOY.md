# Free Website Deployment Guide

This app is a Streamlit app, so the best free website URL is a Streamlit Community Cloud subdomain:

```text
https://your-chosen-name.streamlit.app
```

## Option A: Free Streamlit Website

1. Create or sign in to GitHub: https://github.com/
2. Create a new GitHub repository named `real-time-stocks-analysis`.
3. Upload these files to the repository:

```text
stock_dashboard_app.py
requirements.txt
README.md
.gitignore
DEPLOY.md
```

4. Go to Streamlit Community Cloud: https://share.streamlit.io/
5. Click `Create app`.
6. Select your GitHub repository.
7. Use this main file path:

```text
stock_dashboard_app.py
```

8. Choose a free custom subdomain, for example:

```text
my-stock-analysis
```

Your public website will become:

```text
https://my-stock-analysis.streamlit.app
```

9. Click `Deploy`.

## Option B: Put It Inside Another Website

After the Streamlit app is deployed, you can embed it in another website with:

```html
<iframe
  src="https://your-chosen-name.streamlit.app/?embed=true"
  style="width: 100%; height: 900px; border: 0;"
></iframe>
```

## Important Notes

- A true custom domain like `yourname.com` usually costs money.
- Streamlit gives a free `streamlit.app` subdomain.
- Static hosts like GitHub Pages, Netlify, and Cloudflare Pages can host a normal HTML website for free, but they cannot directly run this Python Streamlit app unless the app itself is hosted somewhere else.
