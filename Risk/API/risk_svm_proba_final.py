# %%
import pandas as pd
import numpy as np
import joblib

from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix

# %%
# Load training data
train = pd.read_csv('/Users/rebuy/Desktop/FCAI/GP/Research Papers/Risk Analysis/5907002/apachejit/dataset/apachejit_train.csv')

# %%
# Preprocessing
X_train = train.drop(['buggy','commit_id','project','fix','year','author_date'], axis=1)
y_train = train['buggy']

# %%
# ====== FIXED SVM MODEL (your chosen params) ======
model = SVC(
    C=10,
    kernel='rbf',
    gamma='scale',
    probability=True
)

# Train model
model.fit(X_train, y_train)

# %%
# Save model
joblib.dump(model, "svm_model.pkl")

# %%
# Load test data
test = pd.read_csv('/Users/rebuy/Desktop/FCAI/GP/Research Papers/Risk Analysis/5907002/apachejit/dataset/apachejit_test_small.csv')

X_test = test.drop(['buggy','commit_id','project','fix','year','author_date'], axis=1)
y_test = test['buggy']

# %%
# Load model
model = joblib.load("svm_model.pkl")

# %%
# ====== PROBABILITY OUTPUT ======
y_prob = model.predict_proba(X_test)[:, 1]   # probability of buggy = 1
y_pred = (y_prob >= 0.5).astype(int)

# %%
# Evaluation
print("Accuracy:", accuracy_score(y_test, y_pred))
print("F1 Score:", f1_score(y_test, y_pred))
print("Confusion Matrix:\n", confusion_matrix(y_test, y_pred))

# %%
# Single prediction example
X_new = pd.DataFrame([[
    223, 33, 7, 5, 2,
    2.21368713,
    0.142857143,
    1.857142857,
    12.14285714,
    104,
    104,
    0.000606057
]], columns=X_train.columns)

probability = model.predict_proba(X_new)[:, 1]

print("Bug probability:", probability[0])