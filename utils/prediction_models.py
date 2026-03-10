import os
import torch
import pickle
import torch.nn as nn
import pandas as pd


class PredictionModels:
    """
    Manages loading and storage of all models and supporting dataframes.
    """
    PLANT_DIAGNOSIS_MODEL = "plant_diagnosis_model.pt"
    FERTILIZER_RECOMMENDATION_MODEL = "fertilizer_recommendation_model.pkl"
    FERTILIZER_CLASSIFIER_MODEL = "fertilizer_classifier_model.pkl"
    CROP_RECOMMENDATION_RF_MODEL = "crop_recommendation_model.pkl"
    CROP_YIELD_PREDICTION_MODEL = "crop_yield_prediction_model.pkl"
    YIELD_DATA_PREPROCESSOR = "yield_data_preprocessor.pkl"

    DISEASE_CSV_FILE = "disease_info.csv"
    SUPPLEMENT_CSV_FILE = "supplement_info.csv"
    CROP_RECOMMENDATION_CSV = "crop_recommendation.csv"

    def __init__(self, models_dir="models", dataset_dir="data"):

        self.models_dir = models_dir
        self.dataset_dir = dataset_dir

        self.disease_info = None
        self.supplement_info = None
        self.plant_diagnoser = None
        self.ferti_model = None
        self.classifier_model = None
        self.crop_model = None
        self.crop_data = None

        self.yield_model = None
        self.yield_preprocessor = None

        self.load_models()

    def _get_model_path(self, filename):
        """Helper to construct the full path for a file in the models directory."""
        return os.path.join(self.models_dir, filename)

    def _get_dataset_path(self, filename):
        """Helper to construct the full path for a file in the data directory."""
        return os.path.join(self.dataset_dir, filename)

    def load_models(self):
        """Loads all dataframes and models from their respective directories."""

        try:
            disease_path = self._get_dataset_path(self.DISEASE_CSV_FILE)
            supplement_path = self._get_dataset_path(self.SUPPLEMENT_CSV_FILE)
            crop_csv_path = self._get_dataset_path(self.CROP_RECOMMENDATION_CSV)

            self.disease_info = pd.read_csv(disease_path, encoding="utf8")
            self.supplement_info = pd.read_csv(supplement_path, encoding="utf8")
            self.crop_data = pd.read_csv(crop_csv_path)

        except FileNotFoundError as e:
            print(f"Error loading CSV data: {e}")
            raise

        try:
            diagnoser_path = self._get_model_path(self.PLANT_DIAGNOSIS_MODEL)

            self.plant_diagnoser = CNN(39)
            self.plant_diagnoser.load_state_dict(
                torch.load(diagnoser_path, map_location=torch.device("cuda" if torch.cuda.is_available() else "cpu"))
            )
            self.plant_diagnoser.eval()
        except Exception as e:
            print(f"Error loading CNN model: {e}")
            raise

        try:
            ferti_path = self._get_model_path(self.FERTILIZER_RECOMMENDATION_MODEL)
            classifier_path = self._get_model_path(self.FERTILIZER_CLASSIFIER_MODEL)

            with open(ferti_path, "rb") as f:
                self.ferti_model = pickle.load(f)
            with open(classifier_path, "rb") as f:
                self.classifier_model = pickle.load(f)
        except Exception as e:
            print(f"Error loading Fertilizer models: {e}")
            raise

        try:
            crop_model_path = self._get_model_path(self.CROP_RECOMMENDATION_RF_MODEL)
            with open(crop_model_path, "rb") as f:
                self.crop_model = pickle.load(f)
        except Exception as e:
            print(f"Error loading Crop Prediction model: {e}")
            raise
       
        try:
            with open(
                os.path.join(self.models_dir, self.CROP_YIELD_PREDICTION_MODEL), "rb"
            ) as f:
                self.yield_model = pickle.load(f)

            with open(
                os.path.join(self.models_dir, self.YIELD_DATA_PREPROCESSOR), "rb"
            ) as f:
                self.yield_preprocessor = pickle.load(f)
        except Exception as e:
            print(f"Error Failed loading Crop Yield models: {e}")
            raise


class CNN(nn.Module):
    def __init__(self, num_classes=39, input_shape=(3, 224, 224)):
        super().__init__()

        layers = []
        in_channels = input_shape[0]

        channel_configs = [32, 64, 128, 256]

        for out_channels in channel_configs:
            layers.extend(self._conv_block(in_channels, out_channels))
            in_channels = out_channels

        self.conv_layers = nn.Sequential(*layers)

        self._calculate_linear_input(input_shape)

        self.dense_layers = nn.Sequential(
            nn.Dropout(0.4),
            nn.Linear(self.linear_input_size, 1024),
            nn.ReLU(inplace=True),
            nn.Dropout(0.4),
            nn.Linear(1024, num_classes),
        )

    def _conv_block(self, in_c, out_c):
        return [
            nn.Conv2d(in_c, out_c, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.BatchNorm2d(out_c),
            nn.Conv2d(out_c, out_c, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.BatchNorm2d(out_c),
            nn.MaxPool2d(kernel_size=2),
        ]

    def _calculate_linear_input(self, input_shape):
        with torch.no_grad():
            dummy_input = torch.zeros(1, *input_shape)
            dummy_output = self.conv_layers(dummy_input)
            self.linear_input_size = dummy_output.flatten(1).shape[1]

    def forward(self, x):
        out = self.conv_layers(x)
        out = torch.flatten(out, 1)
        out = self.dense_layers(out)
        return out
