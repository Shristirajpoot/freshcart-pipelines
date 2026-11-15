# Assignment: From Git to Gold — End-to-End Data Engineering Report

- **Student Name:** Shristi Rajpoot
- **Roll Number:** 23BCS239
- **Course:** Data Engineering · Pipeline Orchestration
- **GitHub Repository:** https://github.com/Shristirajpoot/freshcart-pipelines

---

## Part A: Git and CI/CD (15 marks)

### A1. Repository structure and commit history (5 marks)

**Repository URL:** https://github.com/Shristirajpoot/freshcart-pipelines

```text
freshcart-pipelines/
├── README.md
├── .gitignore                # ignores .env, *.pkl, *.csv, mage.log, __pycache__/
├── requirements.txt
├── elt/
│   └── freshcart_elt.ipynb   # FreshCart ELT + Bonus notebook with all outputs visible
├── iris_project/             # Mage ML project + mage_iris.ipynb with all outputs visible
│   ├── data_loaders/load_iris.py
│   ├── transformers/{check_data.py, prepare_data.py, train_model.py, evaluate_model.py}
│   ├── data_exporters/save_results.py
│   ├── pipelines/iris_classifier/metadata.yaml
│   └── mage_iris.ipynb
├── stream/
│   ├── dispatcher.py
│   ├── driver.py
│   ├── send_d1_keys.py
│   └── stream_colab.ipynb    # RabbitMQ stream execution notebook with outputs
├── tests/
│   └── test_prepare_data.py
└── .github/workflows/ci.yml
```

**Output of `git log --oneline`:**
```text
00ee8a2 Update Mage Iris and RabbitMQ stream notebooks with executed outputs
7a6eaea Update FreshCart ELT notebook with all executed Snowflake and Bonus outputs
37c3aa6 Add Part B/C notebook work, Mage blocks, stream Colab notebook, report draft
e174ea5 Fix test_size back to 0.2
8fc8d02 Break test_size to 0.3 (demo failing CI)
3faea0e Add FreshCart ELT and Mage Iris notebooks
00c6f0a Add elt folder placeholder
f81baa3 Add RabbitMQ dispatcher and driver with ACK/NACK
7db0a21 Add pytest test and GitHub Actions CI workflow
923cce3 Add prepare_data transformer for Iris project
f52d039 Add requirements.txt
6095064 Add README and .gitignore
```

---

### A2. Where does each command act? (4 marks)

| Command | Where the change happens | What exactly happens? |
|---|---|---|
| `git init` | Working folder (initializes local repository `.git/`) | Creates a hidden `.git` directory inside the working folder so Git can start tracking version history locally. |
| `git add train.py` | Working folder → Staging area (index) | Copies the current snapshot of `train.py` from the working folder into the staging area so it is queued for the next commit. |
| `git commit -m "msg"` | Staging area → Local repository | Permanently records a new commit object in the local `.git` repository containing all staged file snapshots and the commit message. |
| `git remote add origin URL` | Local repository configuration (`.git/config`) | Registers the alias `origin` pointing to the remote GitHub repository URL without transferring any files over the network yet. |
| `git push -u origin main` | Local repository → Remote Git (GitHub) | Uploads local commits on the `main` branch to the remote repository on GitHub and sets `origin/main` as the default upstream tracking branch. |
| `git pull origin main` | Remote Git → Local repository + Working folder | Fetches any new commits from `origin/main` on GitHub and merges them into both the local repository history and the working folder files. |

**After running `git commit`, can your teammate see your code on GitHub? Why or why not?**
No. `git commit` only writes the snapshot into the **local repository** (`/.git`) on my own laptop; it does not communicate with GitHub over the network. My teammate can only see the new commits on GitHub after I run `git push`, which transfers the commits from my local repository to the remote repository (`origin`).

---

### A3. A small CI workflow (6 marks)

- **Test file (`tests/test_prepare_data.py`):** Imports `load_iris` from `scikit-learn` and `transform` from `iris_project.transformers.prepare_data`, verifying that the 150-row dataset is split into exactly `120` training rows (`(out["split"] == "train").sum() == 120`) and `30` test rows (`(out["split"] == "test").sum() == 30`).
- **Workflow (`.github/workflows/ci.yml`):** Triggers `on: [push]`, checks out the code (`actions/checkout@v4`), sets up Python 3.12 (`actions/setup-python@v5`), installs `requirements.txt`, and runs `python -m pytest`.
- **Green / Red / Fixed runs:**
  1. **Initial Green Run (`3faea0e`):** `test_size = 0.2` produces 120 train / 30 test rows → `1 passed` (see Appendix Figure A1).
  2. **Intentional Red Run (`8fc8d02`):** Temporarily changing `test_size = 0.3` in `prepare_data.py` produces 105 train / 45 test rows, failing `assert (out["split"] == "train").sum() == 120` with exit code 1 (see Appendix Figure A2).
  3. **Fix Commit (`e174ea5`):** Restoring `test_size = 0.2` returns the workflow to green (see Appendix Figures A3 & A4).

---

## Part B: FreshCart ELT on Snowflake (30 marks)

### B1. Run the baseline (5 marks)

Executed top-to-bottom on Snowflake (`Account: EIDQMJJ-DX74528`, `Role: ACCOUNTADMIN`, `Database: FRESHCART`). All baseline checks match the expected numbers (screenshots in Appendix Figures B1–B3):

| Check | Expected | Actual Output (Snowflake) |
|---|---|---|
| Raw order rows in bronze after one run | 8 (6 web + 2 mobile) | **8** (`6` from `web` + `2` from `mobile`, `ingest_seq` 1..8) |
| Rows that pass cleaning (`silver.orders_clean`) | 6 | **6** (`ORD-1001`, `ORD-1002`×2, `ORD-1003`×2, `ORD-1005`) |
| Rows in quarantine (`quarantine.orders`) | 2 (`ORD-1004`, `ORD-1006`) | **2** (`ORD-1004`: `non_positive_amount`; `ORD-1006`: `bad_email`, `bad_pincode`) |
| Orders after deduplication (`silver.orders_dedup`) | 4 | **4** (`ORD-1001`, `ORD-1002`, `ORD-1003`, `ORD-1005`) |
| Final gold line (`gold.fct_orders`) | 4 orders, revenue 7,785.00, 126 loyalty points | **`GOLD: 4 orders, revenue ₹7785.00, 126 loyalty points`** |
| Share of rows rejected | 25% | **25%** (`2 / 8` checked rows rejected) |

---

### B2. Trace one record by hand (6 marks)

#### Trace of `ORD-1003`
1. **Raw records in `bronze.orders_raw` and why field names differ:**
   - **Web row (`ingest_seq = 2`, `source = 'web'`):** Flat JSON object:
     `{"order_id": "ORD-1003", "cust_email": "meera@outlook.com", "cust_name": "MEERA S", "order_date": "2026-09-02", "amount": null, "currency": "INR", "pincode": "400050", "updated_at": "2026-09-02 09:10:00"}`
   - **Mobile row (`ingest_seq = 8`, `source = 'mobile'`):** Nested JSON object with camelCase keys and `DD/MM/YYYY` date format:
     `{"orderId": "ORD-1003", "customer": {"email": "Meera@Outlook.com", "name": "Meera S"}, "orderDate": "02/09/2026", "total": {"value": "2,100.00", "currency": "INR"}, "deliveryPin": "400050", "updatedAt": "2026-09-02T18:40:00"}`
   - **Why they differ:** The website backend and mobile app were developed as separate services with different JSON schemas. In an ELT architecture, `bronze.orders_raw` stores each API payload untouched in a `VARIANT` column (`raw`) to preserve complete source fidelity.
2. **SQL expressions in `SQL_10_ORDERS_CLEAN` that unify and clean them into `silver.orders_checked`:**
   - **Schema unification (`unified` CTE):** A `UNION ALL` maps `raw:order_id::STRING`, `raw:cust_email::STRING`, `raw:amount::STRING`, `raw:pincode::STRING`, `raw:updated_at::STRING` (where `source = 'web'`) and `raw:orderId::STRING`, `raw:customer.email::STRING`, `raw:total.value::STRING`, `raw:deliveryPin::STRING`, `raw:updatedAt::STRING` (where `source = 'mobile'`) into identical column names.
   - **Type conversion & standardization (`typed` CTE):**
     - `LOWER(TRIM(cust_email))` → `'meera@outlook.com'` for both rows.
     - `INITCAP(RTRIM(TRIM(cust_name), '.'))` → `'Meera S'`.
     - `COALESCE(TRY_TO_DATE(order_date, 'YYYY-MM-DD'), TRY_TO_DATE(order_date, 'DD/MM/YYYY'), TRY_TO_DATE(order_date, 'MON DD, YYYY'))` → parses both `'2026-09-02'` and `'02/09/2026'` to `2026-09-02`.
     - `TRY_TO_DECIMAL(REGEXP_REPLACE(amount, '[^0-9.-]', ''), 12, 2)` → strips the comma from `'2,100.00'` to yield `2100.00` (and keeps `NULL` for the web row).
     - `TRY_TO_TIMESTAMP_NTZ(updated_at)` → parses `'2026-09-02 09:10:00'` and `'2026-09-02T18:40:00'`.
3. **Which copy survives `SQL_20_ORDERS_DEDUP` and why:**
   - The deduplication query uses:
     `QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY updated_at DESC, ingest_seq DESC) = 1`
   - Partitioning by `order_id = 'ORD-1003'`, the mobile copy has `updated_at = 2026-09-02 18:40:00`, which is later than the web copy's `2026-09-02 09:10:00`. Therefore, the mobile copy gets `ROW_NUMBER() = 1` and survives into `silver.orders_dedup` with `amount = 2100.00`.
4. **Arithmetic for `amount_inr` and `loyalty_points` in `gold.fct_orders`:**
   - Currency is `INR`, so `ref.fx_daily` gives `fx_rate = 1.0000`.
   - $	exttt{amount\_inr} = 	ext{ROUND}(2100.00 	imes 1.0000,\ 2) = \mathbf{2100.00}$.
   - Meera (`meera@outlook.com`, `CUST-03`) has tier `Platinum` in `dim.customers_scd2`, which joins to `ref.tier_multiplier` for $	exttt{multiplier} = 3$.
   - $	exttt{loyalty\_points} = \lfloor 2100.00 / 100 floor 	imes 3 = 21 	imes 3 = \mathbf{63}$.

#### Brief Trace of `ORD-1005` vs `ORD-1001` (Priya's Tier Multiplier)
- **Table responsible:** `dim.customers_scd2` (joined with `ref.tier_multiplier` in `SQL_40_GOLD`).
- **Join condition responsible:**
  ```sql
  LEFT JOIN dim.customers_scd2 c
         ON c.email = o.email
        AND o.order_date BETWEEN c.valid_from AND c.valid_to
  ```
- **Why the multiplier changes:** In `dim.customers_scd2`, Priya (`CUST-01`, `priya.r@gmail.com`) has two SCD Type 2 rows:
  1. `Silver` (`multiplier = 1`): `valid_from = 2023-04-10`, `valid_to = 2026-09-02`.
  2. `Gold` (`multiplier = 2`): `valid_from = 2026-09-03`, `valid_to = 9999-12-31`.
  - `ORD-1001` has `order_date = 2026-09-01`, which falls between `2023-04-10` and `2026-09-02` (**Silver**, multiplier `1` → $\lfloor 1250/100 floor 	imes 1 = 12$ points).
  - `ORD-1005` has `order_date = 2026-09-03`, which falls in the second period starting `2026-09-03` (**Gold**, multiplier `2` → $\lfloor 899/100 floor 	imes 2 = 8 	imes 2 = 16$ points).

---

### B3. Add a validation rule (6 marks)

Added inside `ARRAY_CONSTRUCT_COMPACT(...)` in `SQL_10_ORDERS_CLEAN`:
```sql
IFF(COALESCE(currency, '') NOT IN ('INR', 'USD'), 'unsupported_currency', NULL)
```

1. **`reasons` array for `ORD-1006` before and after (`currency = 'EUR'`):**
   - **Before:** `["bad_email", "bad_pincode"]`
   - **After:** `["bad_email", "bad_pincode", "unsupported_currency"]` (see Appendix Figure B4).
2. **Does the gold total change? Why or why not?**
   - **No** (`GOLD: 4 orders, revenue ₹7785.00, 126 loyalty points` before and after). `ORD-1006` was already rejected by `WHERE ARRAY_SIZE(reasons) = 0` because of `bad_email` and `bad_pincode`, so adding a third rejection reason to `ORD-1006` does not remove any new order from `silver.orders_clean`, and all valid orders use `INR` or `USD`.
3. **Does the new run add a second quarantine row for `ORD-1006`? Point to the SQL:**
   - **No** (`quarantine rows for ORD-1006 after: 1`). The `INSERT INTO quarantine.orders` statement in `SQL_10_ORDERS_CLEAN` includes an anti-join guard (`NOT EXISTS`) and deduplication (`QUALIFY ROW_NUMBER()`):
     ```sql
     WHERE ARRAY_SIZE(c.reasons) > 0
       AND NOT EXISTS (
             SELECT 1 FROM quarantine.orders q
             WHERE q.source = c.source
               AND EQUAL_NULL(q.order_id, c.order_id)
               AND EQUAL_NULL(q.row_data:UPDATED_AT::TIMESTAMP_NTZ, c.updated_at))
     ```
     Because `(source='web', order_id='ORD-1006', updated_at='2026-09-04 08:30:00')` already exists in `quarantine.orders` from the earlier run, `NOT EXISTS` evaluates to `FALSE` and prevents inserting a duplicate quarantine row.

---

### B4. Change history and idempotency (7 marks)

Added CRM event: `{"cust_id": "CUST-02", "email": "arjun.k@yahoo.in", "tier": "Gold", "effective_from": "2026-08-15"}`.

| Quantity | My Prediction (before run) | Actual After Run |
|---|---|---|
| Rows for `CUST-02` in `dim.customers_scd2` | **2** (`Silver`: `2024-01-15` to `2026-08-14`; `Gold`: `2026-08-15` to `9999-12-31`) | **2** |
| Tier used for `ORD-1002` | **Gold** (`order_date = 2026-09-01` is $\ge$ `2026-08-15`) | **Gold** |
| Loyalty points for `ORD-1002` | **70** ($	ext{USD } 42.50 	imes 83.20 = ₹3536.00$; $\lfloor 3536/100 floor 	imes 2 = 35 	imes 2 = 70$) | **70** |
| Total loyalty points in gold | **161** ($12 + 70 + 63 + 16 = 161$, up by $+35$ from $126$) | **161** |
| Number of gold rows whose `published_at` changed | **1** (only `ORD-1002`) | **1 (`['ORD-1002']`)** |

**How `row_hash` and `MERGE` make the gold table safe to re-run, and why bronze still grows by 8 rows on every run:**
In `SQL_40_GOLD`, every enriched order row has a deterministic `row_hash = HASH(order_date, cust_id, email, tier, multiplier, amount, ...)` computed across all non-key business attributes. The `MERGE INTO gold.fct_orders t USING (...) s ON t.order_id = s.order_id` matches existing rows by primary key (`order_id`) and only executes `UPDATE` when `WHEN MATCHED AND t.row_hash <> s.row_hash`. When the pipeline is re-run with unchanged data, `t.row_hash <> s.row_hash` is false for all 4 orders, so zero rows are updated or duplicated and `published_at` remains untouched. When Arjun's tier changed to Gold, only `ORD-1002` had a new `tier`, `multiplier`, and `loyalty_points`, changing its `row_hash` and updating solely that 1 row. By contrast, `bronze.orders_raw` is an immutable, append-only landing log loaded via `COPY INTO` from a new timestamped stage folder (`orders_web/{run_id}`, `orders_mobile/{run_id}`) on every run, so it intentionally appends 8 raw records per run while `SQL_20_ORDERS_DEDUP` collapses duplicates downstream.

---

### B5. Add one data-quality check (6 marks)

- **Sixth check added to `quality_checks()`:**
  ```python
  "gold orders with amount but NULL amount_inr":
      "SELECT COUNT_IF(amount_inr IS NULL AND amount IS NOT NULL) FROM gold.fct_orders"
  ```
- **Making the check fail on purpose:** Appended mock order `ORD-9001` (`amount = "10.00"`, `currency = "USD"`, `order_date = "2026-08-20"`). Because `2026-08-20` is earlier than the first FX rate in `MOCK_FX_RESPONSES` (`2026-09-01`), the left join to `ref.fx_daily` produces `fx_rate = NULL` and `amount_inr = NULL`. Running `run_pipeline()` printed (see Appendix Figure B6):
  ```text
  orders with an amount but no FX rate          1   PROBLEM
  gold orders with amount but NULL amount_inr   1   PROBLEM
  ```
- **Removing the mock order:** Removed `ORD-9001` from `MOCK_WEB_ORDERS` and deleted its appended row from `bronze.orders_raw` and `gold.fct_orders`. Re-running `run_pipeline()` returned all six checks to `0   OK` (see Appendix Figure B7).

**Why ELT is a better choice than ETL for FreshCart, and when ETL would still win:**
ELT is better for FreshCart because raw web, mobile, and CRM payloads arrive in different JSON shapes, and storing them untouched in Snowflake `bronze` (`VARIANT`) lets us evolve validation rules (like B3's `unsupported_currency`) or historical SCD2 dimensions (like B4's backdated Gold upgrade) simply by re-running SQL transformations without re-fetching from source APIs. It also leverages Snowflake's scalable warehouse compute for joins, window-function deduplication, and point-in-time enrichment. **ETL would still win** when strict data-privacy/compliance regulations (such as GDPR/HIPAA PII masking or PCI card-number scrubbing) require sensitive fields to be stripped or anonymized *before* the data ever lands in cloud storage, or when streaming high-volume telemetry where pre-filtering before ingestion saves massive storage/network costs.

---

## Part C: ML pipeline with Mage (20 marks)

### C1. Draw and run the pipeline (4 marks)

**Baseline Block Graph (`load_iris` → `prepare_data` → `train_model` → `save_results`):**

![Mage Block Graph](c1_diagram.png)

**Output of `mage run iris_project iris_classifier --test`:**
```text
Rows loaded: 150
--------------------------------------------------------------
1/1 tests passed.
Train rows: 120 | Test rows: 30
--------------------------------------------------------------
1/1 tests passed.
max_depth = 3 | Test accuracy = 1.0
--------------------------------------------------------------
1/1 tests passed.
Saved 30 predictions to iris_predictions.csv
Pipeline run completed.
```

---

### C2. Tests as a gate (6 marks)

Executed for `max_depth = 1, 2, 3, 4, 5` after deleting `iris_predictions.csv` before each run:

| `max_depth` | Test accuracy | `test_accuracy` passed? | `iris_predictions.csv` created? |
|---|---|---|---|
| **1** | **0.633** | **False** (`AssertionError: Model accuracy is below 80%`) | **False** |
| **2** | **0.967** | **True** | **True** |
| **3** | **1.000** | **True** | **True** |
| **4** | **1.000** | **True** | **True** |
| **5** | **1.000** | **True** | **True** |

**How a failing `@test` in `train_model` stops `save_results` from running, and why this is better than saving and checking afterwards:**
In Mage, every `@test` function decorated inside a block is executed by the pipeline executor immediately after the block's main function returns its output and *before* any downstream block tasks are scheduled. When `max_depth = 1`, `train_model` achieves `0.633` accuracy, so `assert accuracy >= 0.8` inside `test_accuracy` raises an `AssertionError`, causing Mage to mark `train_model` as failed (`Exception: Failed to pass tests for block train_model`) and abort the DAG before `save_results` ever starts. Acting as a pre-export gate is much safer than saving the file first and checking afterwards because downstream consumers, dashboards, or automated jobs can never accidentally read a corrupted or low-accuracy `iris_predictions.csv` during the window between file creation and post-hoc validation.

---

### C3. Add the evaluation branch (5 marks)

Added `evaluate_model.py` (`@transformer`) so `train_model` fans out to two parallel downstream blocks (`[save_results, evaluate_model]`), and added C4's `check_data` block after `load_iris`.

**Edited `iris_project/pipelines/iris_classifier/metadata.yaml`:**
```yaml
blocks:
- name: load_iris
  uuid: load_iris
  type: data_loader
  language: python
  upstream_blocks: []
  downstream_blocks: [check_data]
- name: check_data
  uuid: check_data
  type: transformer
  language: python
  upstream_blocks: [load_iris]
  downstream_blocks: [prepare_data]
- name: prepare_data
  uuid: prepare_data
  type: transformer
  language: python
  upstream_blocks: [check_data]
  downstream_blocks: [train_model]
- name: train_model
  uuid: train_model
  type: transformer
  language: python
  upstream_blocks: [prepare_data]
  downstream_blocks: [save_results, evaluate_model]
- name: save_results
  uuid: save_results
  type: data_exporter
  language: python
  upstream_blocks: [train_model]
  downstream_blocks: []
- name: evaluate_model
  uuid: evaluate_model
  type: transformer
  language: python
  upstream_blocks: [train_model]
  downstream_blocks: []
name: iris_classifier
uuid: iris_classifier
type: python
variables:
  max_depth: 3
```

**Confusion Matrix (`max_depth = 3`, 30 test rows) and Metrics Table:**

```text
Confusion matrix:
predicted   0  1   2
actual              
0          10  0   0
1           0  9   0
2           0  0  11
```

| Metric | Value |
|---|---|
| `accuracy` | **1.000** |
| `precision` (macro) | **1.000** |
| `recall` (macro) | **1.000** |
| `f1_score` (macro) | **1.000** |

*(Screenshot of the branched pipeline in the Mage UI via Cloudflare tunnel is included in Appendix Figure C1).*

---

### C4. Your own block (5 marks)

Added transformer `iris_project/transformers/check_data.py` between `load_iris` and `prepare_data` with its own `@test` gate (`test_no_missing_and_3_classes`):
```python
@transformer
def check_data(df, *args, **kwargs):
    print('Missing values:', int(df.isna().sum().sum()), '| classes:', df['target'].nunique())
    return df

@test
def test_no_missing_and_3_classes(output, *args):
    assert output.isna().sum().sum() == 0, 'Data contains missing values'
    assert output['target'].nunique() == 3, 'Expected exactly 3 classes'
```
- **Pipeline output:** `Missing values: 0 | classes: 3` → `1/1 tests passed.`
- Committed to the repository and verified that GitHub Actions CI continues to pass.

---

## Part D: Food-order stream with RabbitMQ (20 marks)

### D1. Routing on paper (6 marks)

Driver bindings:
- **Ravi:** `bangalore.koramangala.*`
- **Priya:** `bangalore.indiranagar.*`
- **Arjun:** `bangalore.*.ride`
- **Meena:** `bangalore.*.food`
- **Karthik:** `chennai.tnagar.food`
- **Control:** `bangalore.#`

| # | Routing key | Receiving queues (Prediction & Verified Output) |
|---|---|---|
| **1** | `bangalore.koramangala.food` | **Ravi, Meena, Control** |
| **2** | `bangalore.indiranagar.ride` | **Priya, Arjun, Control** |
| **3** | `bangalore.whitefield.ride` | **Arjun, Control** |
| **4** | `chennai.tnagar.food` | **Karthik** |
| **5** | `chennai.whitefield.ride` | **dropped** (no queue binding matches) |
| **6** | `bangalore.koramangala` | **Control** |

**Careful explanation for Question 6 (`bangalore.koramangala` — two words):**
In a RabbitMQ `topic` exchange, routing keys and binding patterns are split into dot-separated words:
- `*` (star) matches **exactly one word**. Therefore, `bangalore.koramangala.*` (Ravi), `bangalore.indiranagar.*` (Priya), `bangalore.*.ride` (Arjun), and `bangalore.*.food` (Meena) all require **three** words in the routing key and **cannot match** the two-word key `bangalore.koramangala`. `chennai.tnagar.food` (Karthik) also requires three words starting with `chennai` and cannot match.
- `#` (hash) matches **zero or more words**. In Control's pattern `bangalore.#`, the first word matches `bangalore` and `#` matches the single remaining word `koramangala` (or even zero extra words). Thus, **only Control** receives message #6.

---

### D2. Build it (8 marks)

Implemented `stream/dispatcher.py` and `stream/driver.py` using `pika` and ran all 6 drivers plus the dispatcher for 2 minutes (60 messages) in `stream/stream_colab.ipynb`:
- **Verification of D1 keys (`send_d1_keys.py` output):**
  ```text
  published D1 row 1: key=bangalore.koramangala.food  -> ['Ravi', 'Meena', 'Control']
  published D1 row 2: key=bangalore.indiranagar.ride  -> ['Priya', 'Arjun', 'Control']
  published D1 row 3: key=bangalore.whitefield.ride   -> ['Arjun', 'Control']
  published D1 row 4: key=chennai.tnagar.food         -> ['Karthik']
  published D1 row 5: key=chennai.whitefield.ride     -> dropped
  published D1 row 6: key=bangalore.koramangala       -> ['Control']
  ```
- **2-minute run summary across drivers:**
  `Ravi: 7 ACKed, 0 NACKed | Priya: 13 ACKed, 3 NACKed | Arjun: 16 ACKed, 4 NACKed | Meena: 12 ACKed, 1 NACKed | Karthik: 7 ACKed, 0 NACKed | Control: 29 ACKed, 5 NACKed`

---

### D3. ACK and NACK (6 marks)

Every 10th message (`#10, #20, #30, #40, #50, #60`), `dispatcher.py` omits the `"zone"` field from the JSON body. `driver.py` inspects `if "zone" not in req:` and rejects bad messages with `channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)` while acknowledging valid messages with `channel.basic_ack(delivery_tag=method.delivery_tag)`.

**Console output excerpt from `driver_Control.log`:**
```text
[Control] GOT   key=bangalore.indiranagar.ride {'id': 6, 'city': 'bangalore', 'zone': 'indiranagar', 'type': 'ride', 'ts': '2026-11-15T12:23:00.962918+00:00'} -> ACK
[Control] BAD   key=bangalore.indiranagar.ride {'id': 10, 'city': 'bangalore', 'type': 'ride', 'ts': '2026-11-15T12:23:08.965387+00:00'} -> NACK (discarded)
[Control] GOT   key=bangalore.whitefield.ride {'id': 13, 'city': 'bangalore', 'zone': 'whitefield', 'type': 'ride', 'ts': '2026-11-15T12:23:14.967730+00:00'} -> ACK
[Control] BAD   key=bangalore.indiranagar.ride {'id': 20, 'city': 'bangalore', 'type': 'ride', 'ts': '2026-11-15T12:23:28.973127+00:00'} -> NACK (discarded)
```

1. **What happens to a message if the driver crashes *before* sending an ACK?**
   Because `auto_ack=False` (manual acknowledgement mode), RabbitMQ keeps the message in an unacknowledged state until it receives `basic_ack`. If the driver process crashes or its TCP connection drops before sending `basic_ack`, RabbitMQ detects the closed channel, automatically marks the message as ready again (`redelivered = True`), and re-queues it so another consumer (or the driver when it restarts) receives it—guaranteeing at-least-once delivery without message loss.
2. **What would happen with `requeue=True` for a message that is always bad?**
   If a permanently malformed ("poison") message is rejected with `basic_nack(requeue=True)`, RabbitMQ places it right back at the head of the queue and immediately redelivers it to the same driver, which fails validation again and NACKs it with `requeue=True` again. This creates an **infinite redelivery loop** that pegs CPU/network bandwidth and blocks valid messages behind it; using `requeue=False` discards the poison message (or routes it to a Dead-Letter Exchange if configured).

---

## Part E: Integration Diagram and Reflection (15 marks)

### E1. End-to-End Platform Integration Diagram

![End-to-End Integration Diagram](e_diagram.png)

### E2. Half-Page Reflection: One Thing That Broke, How I Found the Cause, and How I Fixed It

While implementing **Part B5 (Data-Quality Check)** and **Part B1 (Snowflake Authentication)**, two instructive issues broke our pipeline and deepened my understanding of ELT architecture:

1. **The "Ghost" Bad Order in an Append-Only Bronze Layer (B5):**
   - **What broke:** In B5, after adding the sixth quality check (`gold orders with amount but NULL amount_inr`), we intentionally appended a bad order (`ORD-9001`, dated `2026-08-20` in `USD`, before the FX table's `2026-09-01` start date) to `MOCK_WEB_ORDERS` and ran `run_pipeline()`. As expected, the check printed `1 PROBLEM`. However, when we simply removed `ORD-9001` from the Python list `MOCK_WEB_ORDERS` and re-ran `run_pipeline()`, the check *still* reported `1 PROBLEM` and `gold.fct_orders` still had 5 orders instead of 4!
   - **How I found the cause:** Tracing the SQL from `SQL_10_ORDERS_CLEAN` to `SQL_40_GOLD`, I realized that `bronze.orders_raw` is **append-only** (loaded via `COPY INTO`), and `SQL_40_GOLD` uses `MERGE INTO gold.fct_orders` (which inserts/updates matching keys, but never deletes keys that disappear from the latest batch). Even though the new `run_id` file no longer contained `ORD-9001`, `SQL_10_ORDERS_CLEAN` reads `FROM bronze.orders_raw` across *all* historical runs, so `ORD-9001` from the previous run stayed in `bronze.orders_raw`, flowed through `silver.orders_dedup`, and remained in `gold.fct_orders`.
   - **How I fixed it:** Alongside removing `ORD-9001` from `MOCK_WEB_ORDERS`, I executed explicit cleanup statements (`DELETE FROM bronze.orders_raw WHERE raw:order_id::STRING = 'ORD-9001'` and `DELETE FROM gold.fct_orders WHERE order_id = 'ORD-9001'`) before re-running `run_pipeline()`, immediately restoring all six quality checks to `0 OK`.

2. **Snowflake `NAME` vs `LOGIN_NAME` with Google SSO (B1):**
   - **What broke:** Because my Snowflake trial account was created via Google Sign-In (`authenticator = "externalbrowser"`), connecting from Google Colab with `snowflake.connector` initially failed with `390100 (28000): Incorrect username or password was specified`.
   - **How I found the cause & fixed it:** Running `SELECT CURRENT_USER();` inside a Snowflake worksheet revealed that my internal Snowflake object `NAME` was `23bcs239` while my `LOGIN_NAME` was `23BCS239@IIITDMJ.AC.IN`, and Google-created accounts have no password set by default. Running `ALTER USER "23bcs239" SET PASSWORD = '...' MUST_CHANGE_PASSWORD = FALSE;` in Snowflake and passing `user="23BCS239@IIITDMJ.AC.IN"` to `snowflake.connector.connect()` resolved the login immediately.

---

## Bonus: Stream into the Lakehouse (+10 marks)

Connected Part D (RabbitMQ) to Part B (FreshCart Snowflake ELT) at the end of `elt/freshcart_elt.ipynb`:
1. Published 3 new FreshCart-style orders (`ORD-2001`: ₹1,500 INR; `ORD-2002`: ₹800 INR; `ORD-2003`: $20 USD on `2026-09-06` = ₹1,662 INR at carried-forward rate `83.10`) to RabbitMQ queue `freshcart-orders`.
2. `consume_orders(seconds=60)` collected the messages for 1 minute and acknowledged each with `basic_ack`.
3. `write_landing("web", msgs, run_id)` saved the batch as `/content/freshcart_landing/web/web__20261115_111321_stream.json.gz`, `load_file()` staged and copied the 3 rows into `bronze.orders_raw`, and `transform_all(run_id)` executed `SQL_10` through `SQL_40_GOLD`.
4. **First batch run result:** `GOLD: (7, Decimal('11747.00'), 247)` ($7785 + 1500 + 800 + 1662 = ₹11,747.00$; $161 + 30 + 24 + 32 = 247$ points).
5. **Second batch run result (idempotency proof):** Running `stream_batch(60)` a second time loaded 3 more raw rows into `bronze.orders_raw`, but `SQL_20_ORDERS_DEDUP` and `SQL_40_GOLD`'s `MERGE` with `row_hash` left `gold.fct_orders` completely unchanged at **`GOLD: (7, Decimal('11747.00'), 247)`** (see Appendix Figure B8).
