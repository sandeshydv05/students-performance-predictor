# Students Performance Predictor

A Flask application that estimates an examination mark from student learning indicators, assigns a performance category, and stores prediction history in SQLite. Predictions are decision-support estimates—not a measure of a student's full potential.

## Architecture

- **Browser:** Responsive Bootstrap/CSS interface; Chart.js renders outcome and recent-prediction charts.
- **Flask (`app.py`):** Validates form input, calls the persisted scikit-learn pipeline, generates suggestions, and provides student record CRUD routes.
- **Model pipeline (`train_model.py`):** Reads the training CSV with pandas, imputes missing feature values, scales numeric inputs, one-hot encodes categories, selects the top features, compares three regressors, and persists the lowest-MAE candidate with Joblib.
- **Storage:** SQLite stores student inputs and prediction history in `database/students.db`.
- **Evaluation:** MAE, MSE, RMSE, and R² are printed and saved in `model_metrics.json`. A Seaborn/Matplotlib comparison chart is written to `static/images/model_comparison.png`.

## Project structure

```text
Students performance predictor/
├── app.py
├── train_model.py
├── requirements.txt
├── README.md
├── students.csv
├── student_model.pkl              # created by training
├── model_metrics.json              # created by training
├── database/
│   └── students.db                 # created by the Flask app
├── static/
│   ├── css/style.css
│   ├── js/script.js
│   └── images/model_comparison.png # created by training
└── templates/
    ├── base.html
    ├── index.html
    ├── dashboard.html
    ├── predict.html
    ├── results.html
    └── students.html
```

## Dataset format

`students.csv` is a small illustrative sample dataset (not a real or validated institutional dataset). It contains one row per student and these columns:

| Column | Type / allowed values | Meaning |
|---|---|---|
| `study_hours` | Number, 0–16 | Average focused study hours per day |
| `attendance` | Number, 0–100 | Attendance percentage |
| `previous_marks` | Number, 0–100 | Previous examination marks |
| `assignment_marks` | Number, 0–100 | Assignment marks |
| `sleep_hours` | Number, 0–24 | Average sleep hours per night |
| `parental_education` | `None`, `High School`, `Some College`, `Bachelor`, `Master` | Highest reported parental education level |
| `internet_access` | `Yes` or `No` | Internet available at home |
| `extracurricular` | `Yes` or `No` | Participates in extracurricular activities |
| `exam_marks` | Number, 0–100 | Training target; omitted from prediction input |

Keep the feature names and categories consistent when replacing the sample CSV. Feature columns can contain missing values; missing target rows are excluded from training. The application validation requires complete prediction inputs.

## Installation and run (VS Code / Windows PowerShell)

1. Open this folder in VS Code and open a terminal in the project directory.
2. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again.

3. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Train and compare the models:

   ```powershell
   python train_model.py
   ```

   This creates `student_model.pkl`, `model_metrics.json`, and the model comparison image.

5. Start the application:

   ```powershell
   python app.py
   ```

6. Open `http://127.0.0.1:5000` in a browser. The SQLite database is initialized automatically.

The interface loads Bootstrap, Chart.js, and fonts from CDNs, so internet access is needed for those external visual assets; prediction, Flask, and SQLite run locally. Debug mode is off by default; set `$env:FLASK_DEBUG = "1"` before `python app.py` if you need the Flask development debugger. For anything beyond local development, set a private `FLASK_SECRET_KEY` and use an appropriate production server.

## Test the prediction and records

1. Open **New prediction** and enter a student name or ID, then provide values within each displayed range.
2. Submit the form. The result page shows the model-generated estimate, performance category, supplied indicators, and suggestions; the record is saved in SQLite.
3. Open **Student records** to search and view saved records, edit a record (which recalculates its estimate), or delete it.
4. Return to **Overview** to inspect aggregate counts, category distribution, recent prediction trend, and model evaluation.
5. Verify validation by submitting a value outside the form's allowed range or leaving a required field blank; the app displays an error and does not create a record.

For reproducible model comparisons, `train_model.py` uses a fixed random seed and a held-out test split. Metrics from this small synthetic sample are for demonstrating the workflow only; replace it with representative, consented, appropriately governed data before using estimates in real educational decisions.
