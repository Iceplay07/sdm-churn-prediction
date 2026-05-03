from pathlib import Path
 
 
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "features.csv"
MODEL_DIR = ROOT / "model"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
 
ARTIFACTS_DIR = MODEL_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
 
RANDOM_STATE = 42
TEST_SIZE = 0.20
CV_SPLITS = 5
 
CAT_FEATURES = ["gender", "geography"]
DROP_COLS = ["client_id", "churned_in_next_28d", "already_churned_at_snapshot"]
TARGET = "churned_in_next_28d"
 
TARGET_PRECISION = 0.75
TARGET_RECALL = 0.70
 
MODEL_PARAMS = dict(
    iterations=3000,
    depth=6,
    learning_rate=0.03,
    l2_leaf_reg=5.0,
    min_data_in_leaf=20,
    early_stopping_rounds=100,
)