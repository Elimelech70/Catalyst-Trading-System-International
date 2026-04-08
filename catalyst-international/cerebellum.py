"""
Cerebellum — Trained Neural Pattern Recognition

The cerebellum handles the routine. Claude AI handles only what requires
genuine reasoning (the 6% principle).

Two models:
  - CandleModel: OHLCV sequence -> direction + confidence + predicted return
  - NewsToSecurityModel: headline + source -> security + direction + confidence

Models are ONNX files deployed from the laptop (neural_claude) via SCP.
If models are not present, the coordinator falls back to LLM-only mode.

Version: 1.0.0
"""

import json
import logging
import os
from typing import Optional

import numpy as np

logger = logging.getLogger("cerebellum")


class CandleModel:
    """
    Candle pattern classifier using ONNX inference.

    Input:  OHLCV candle sequence (N candles x 5 features)
    Output: direction (bullish/bearish/neutral), confidence (0-1), predicted returns
    """

    def __init__(self, model_path: str):
        self.model_path = model_path
        self.loaded = False
        self.session = None
        self._load()

    def _load(self):
        if not os.path.isfile(self.model_path):
            logger.info(f"CandleModel: No model at {self.model_path}")
            return
        try:
            import onnxruntime as ort
            self.session = ort.InferenceSession(
                self.model_path,
                providers=["CPUExecutionProvider"],
            )
            self.loaded = True
            logger.info(f"CandleModel: Loaded from {self.model_path}")
        except ImportError:
            logger.warning("CandleModel: onnxruntime not installed")
        except Exception as e:
            logger.error(f"CandleModel: Failed to load: {e}")

    def predict(self, candle_sequence: list) -> dict:
        """
        Run inference on a candle sequence.

        Args:
            candle_sequence: List of dicts with keys: open, high, low, close, volume
                             Or a numpy array of shape (N, 5)

        Returns:
            dict with: direction, confidence, predicted_return_5m, predicted_return_15m
        """
        if not self.loaded or not self.session:
            return {"available": False, "reason": "model not loaded"}

        try:
            # Convert to numpy array if needed
            if isinstance(candle_sequence, list):
                arr = np.array([
                    [c.get("open", 0), c.get("high", 0), c.get("low", 0),
                     c.get("close", 0), c.get("volume", 0)]
                    for c in candle_sequence
                ], dtype=np.float32)
            else:
                arr = np.array(candle_sequence, dtype=np.float32)

            # Normalize: percent change from first candle
            if arr.shape[0] > 0 and arr[0, 3] > 0:
                base_price = arr[0, 3]  # first close
                arr[:, :4] = (arr[:, :4] - base_price) / base_price
                if arr[0, 4] > 0:
                    arr[:, 4] = arr[:, 4] / arr[0, 4]  # volume ratio

            # Add batch dimension: (1, N, 5)
            input_data = arr.reshape(1, -1, 5)

            input_name = self.session.get_inputs()[0].name
            outputs = self.session.run(None, {input_name: input_data})

            # Interpret output based on model structure
            # Default expectation: outputs[0] = [bullish_prob, bearish_prob, neutral_prob]
            probs = outputs[0][0]
            directions = ["bullish", "bearish", "neutral"]
            idx = int(np.argmax(probs))
            confidence = float(probs[idx])

            result = {
                "available": True,
                "direction": directions[idx] if idx < len(directions) else "neutral",
                "confidence": round(confidence, 4),
                "probabilities": {d: round(float(p), 4) for d, p in zip(directions, probs)},
            }

            # Optional: predicted returns if model has second output
            if len(outputs) > 1:
                returns = outputs[1][0]
                result["predicted_return_5m"] = round(float(returns[0]), 6) if len(returns) > 0 else None
                result["predicted_return_15m"] = round(float(returns[1]), 6) if len(returns) > 1 else None

            return result

        except Exception as e:
            logger.error(f"CandleModel inference error: {e}")
            return {"available": False, "reason": str(e)}


class NewsToSecurityModel:
    """
    News-to-security classifier using ONNX inference.

    Input:  headline text, source tier, timestamp
    Output: security symbol, direction, confidence
    """

    def __init__(self, model_path: str):
        self.model_path = model_path
        self.loaded = False
        self.session = None
        self._load()

    def _load(self):
        if not os.path.isfile(self.model_path):
            logger.info(f"NewsToSecurityModel: No model at {self.model_path}")
            return
        try:
            import onnxruntime as ort
            self.session = ort.InferenceSession(
                self.model_path,
                providers=["CPUExecutionProvider"],
            )
            self.loaded = True
            logger.info(f"NewsToSecurityModel: Loaded from {self.model_path}")
        except ImportError:
            logger.warning("NewsToSecurityModel: onnxruntime not installed")
        except Exception as e:
            logger.error(f"NewsToSecurityModel: Failed to load: {e}")

    def predict(self, headline: str, source_tier: int = 3, timestamp: str = "") -> dict:
        """
        Run inference on a news headline.

        Returns:
            dict with: security, direction, confidence
        """
        if not self.loaded or not self.session:
            return {"available": False, "reason": "model not loaded"}

        try:
            # Simple tokenization: character-level or word-level encoding
            # The actual encoding must match what the model was trained on
            tokens = np.array([ord(c) for c in headline[:256]], dtype=np.float32)
            # Pad to fixed length
            padded = np.zeros(256, dtype=np.float32)
            padded[:len(tokens)] = tokens[:256]

            # Add source tier as feature
            input_data = np.concatenate([padded, [float(source_tier)]]).reshape(1, -1)

            input_name = self.session.get_inputs()[0].name
            outputs = self.session.run(None, {input_name: input_data})

            # Interpret: outputs[0] = security probabilities, outputs[1] = direction
            result = {
                "available": True,
                "raw_output": [float(x) for x in outputs[0][0][:5]],
                "confidence": round(float(np.max(outputs[0][0])), 4),
            }

            if len(outputs) > 1:
                direction_probs = outputs[1][0]
                result["direction"] = "bullish" if direction_probs[0] > direction_probs[1] else "bearish"
                result["direction_confidence"] = round(float(max(direction_probs)), 4)

            return result

        except Exception as e:
            logger.error(f"NewsToSecurityModel inference error: {e}")
            return {"available": False, "reason": str(e)}


class Cerebellum:
    """
    The cerebellum: fast, automatic pattern recognition. No tokens. No API calls.

    Loads ONNX models from a configured directory. If models are missing,
    the coordinator falls back to LLM-only mode gracefully.
    """

    DEFAULT_MODELS_PATH = "/app/models"

    def __init__(self, models_path: Optional[str] = None):
        self.models_path = models_path or os.getenv(
            "CEREBELLUM_MODELS_PATH", self.DEFAULT_MODELS_PATH
        )
        self.candle_model = CandleModel(
            os.path.join(self.models_path, "candle_model.onnx")
        )
        self.news_model = NewsToSecurityModel(
            os.path.join(self.models_path, "news_model.onnx")
        )
        self._version = self._load_version()

    def _load_version(self) -> dict:
        version_path = os.path.join(self.models_path, "model_version.json")
        try:
            with open(version_path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"version": "unknown", "deployed_at": "unknown"}

    def is_loaded(self) -> bool:
        """True if at least one model is loaded and ready for inference."""
        return self.candle_model.loaded or self.news_model.loaded

    def status(self) -> dict:
        return {
            "candle_model": self.candle_model.loaded,
            "news_model": self.news_model.loaded,
            "models_path": self.models_path,
            "version": self._version,
        }
