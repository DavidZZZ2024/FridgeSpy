# Fridge Price Tracker

## Overview

This project is an automated data pipeline that collects refrigerator product information from **The Good Guys** website on a daily schedule.

A Python scraper running on a personal computer extracts product data, uploads the processed dataset to **AWS S3**, and loads it into **Snowflake** for analysis and historical price tracking.

---

## Architecture

```text
Windows Task Scheduler
        │
        ▼
 Python Selenium Scraper
        │
        ▼
 Data Cleaning (Pandas)
        │
        ▼
      AWS S3
        │
        ▼
 Snowflake Stage
        │
        ▼
 Snowflake Table
```

---

## Features

* Daily automated web scraping
* Handles dynamically loaded content using Selenium
* Automatically closes pop-up dialogs
* Automatically clicks **Load More** until all products are loaded
* Extracts product information including brand, model, price, and rating
* Cleans and removes duplicate records
* Uploads processed CSV files to AWS S3
* Loads data into Snowflake for analytics
* Generates execution logs for monitoring and troubleshooting

---

## Technologies

* Python
* Selenium
* Pandas
* AWS S3
* Snowflake
* Windows Task Scheduler
* ChromeDriver
* webdriver-manager

---

## Data Collected

| Field      | Description         |
| ---------- | ------------------- |
| date       | Scrape date         |
| retailer   | Retailer name       |
| brand      | Product brand       |
| title      | Product title       |
| model      | Model number        |
| price_text | Original price text |
| price      | Clean numeric price |
| rating     | Customer rating     |

---

## Workflow

1. Windows Task Scheduler launches the scraper once per day.
2. Selenium opens **The Good Guys** refrigerator category.
3. Pop-up dialogs are dismissed automatically.
4. The scraper repeatedly clicks **Load More** until all products are displayed.
5. Product information is extracted and cleaned.
6. Duplicate records are removed.
7. The processed data is uploaded to AWS S3 as a CSV file.
8. Snowflake ingests the data into a structured table for analysis.

---

## Project Structure

```text
.
├── scraper.py
├── requirements.txt
├── README.md
└── task_run.log
```

---

## How to Run

Install the required packages:

```bash
pip install -r requirements.txt
```

Run the scraper:

```bash
python scraper.py
```

The following environment variables are optional:

| Variable         | Default                  |
| ---------------- | ------------------------ |
| BUCKET           | fridge-tgg-scrape-bucket |
| PROCESSED_PREFIX | processed/               |
| HEADLESS         | 1                        |

---

## Future Improvements

* Deploy the scraper to AWS Lambda or EC2
* Support additional retailers
* Add email notifications for failures
* Build a dashboard for historical price trends
* Implement retry logic and monitoring
* Schedule the entire pipeline in the cloud

---

## Disclaimer

This project was created for educational and portfolio purposes. Website content belongs to its respective owner. Please ensure your use complies with the website's Terms of Service and applicable laws.
