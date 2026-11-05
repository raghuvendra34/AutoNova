# Deployment

## Recommended route: Streamlit Community Cloud

This project now has a Streamlit entry point at `app.py`. It reads the cleaned
CSV files in `data/clean/`, so it can be deployed without exposing the SQLite
database or requiring a separate backend.

### Publish steps

1. Create a public GitHub repository named `omnichannel-analytics`.
2. Push this project folder to the repository's `main` branch.
3. Open Streamlit Community Cloud and choose **New app**.
4. Select the `omnichannel-analytics` repository, branch `main`, and main file
   path `app.py`.
5. Deploy. Streamlit installs the packages listed in `requirements.txt`.

### Local check

```bash
pip install -r requirements.txt
streamlit run app.py
```

### Honesty note for the deployed page

The dashboard uses synthetic data generated for this portfolio project. The
live app states this clearly in the header. Do not describe the results as
real company performance.
