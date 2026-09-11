# TopStokee → Temu scraper

Version 1.3 routes TopStokee requests through a protected Cloudflare Worker, because TopStokee blocks GitHub-hosted runner addresses with HTTP 403. The Worker is restricted to `topstokee.com` and requires a secret token. Browser TLS/HTTP2 impersonation and the CloudCart AJAX fallback remain available.

The scraper scans all products on `topstokee.com`, reads the CloudCart product data, and populates the supplied Temu template. Product discovery automatically falls back from the sitemap index to direct product sitemaps and then to the complete product catalogue when a GitHub runner receives HTTP 403.

## What it does

- scans the whole site in `full` mode;
- exports each sellable variation on a separate row;
- splits mixed adult and children's sizes into separate Temu parent products;
- uses the live discounted price and keeps the old price as the list price when available;
- collects up to 10 SKU images and available detail/size-guide images;
- removes the promotional delivery/payment/exchange text from descriptions;
- splits output automatically into files of at most 1,900 data rows;
- produces a raw CSV, a skipped-products CSV, a log, and a summary.

## GitHub Actions

### 1. Finish the Cloudflare Worker

1. Open the existing `topstokee-proxy` Worker and choose **Edit code**.
2. Replace the test code with `cloudflare-worker.js` from this package and deploy it.
3. Open the Worker's **Settings → Variables and Secrets**.
4. Add a **Secret** named `PROXY_TOKEN` with a long random value. Do not put this value directly in the Worker source.

### 2. Add the same secret to GitHub

1. Open the GitHub repository and choose **Settings → Secrets and variables → Actions**.
2. Choose **New repository secret**.
3. Name: `TOPSTOKEE_PROXY_TOKEN`.
4. Value: exactly the same value used for `PROXY_TOKEN` in Cloudflare.

The Worker URL is already set in `config.json` as `https://topstokee-proxy.hkolev-inc.workers.dev`. If the Worker address changes, update `proxy_url` there.

### 3. Run the scraper

1. Upload every file and folder from this package to the GitHub repository. Keep `.github/workflows/scraper.yml` in the same path.
2. Open **Actions → TopStokee Temu scraper → Run workflow**.
3. First choose `test`, leave `max_products` at `0`, set `workers` to `3`, and run it. Test mode scans 15 products.
4. Download the `topstokee-temu-results` artifact and test one generated XLSX in Temu.
5. After the test succeeds, run again with `mode = full` and `max_products = 0`.

A full run currently discovers about 2,300 product pages and can take roughly 45–90 minutes, depending on the site's response time. GitHub Actions keeps the generated files as a downloadable artifact.

## Assumptions to review in `config.json`

- quantity is `10` for every sellable variation because the site does not publish exact stock quantities;
- shipping template is `OFIS`, taken from the supplied Temu file;
- manufacturer is `TOP STOKE EOOD`, taken from the supplied Temu file;
- country of origin is set to `Bulgaria`;
- color is `Multicolor` when CloudCart does not publish a color variation;
- package weight/dimensions and fallback fabric composition use product-type defaults in `scraper.py`.

Products for which the supplied Temu template has no suitable category, such as standalone sweatpants or backpacks, are not forced into an incorrect category. They are listed in `topstokee_skipped_products.csv`.

## Local run

```bash
python -m pip install -r requirements.txt
python scraper.py --mode test
python scraper.py --mode full --max-products 0
```
