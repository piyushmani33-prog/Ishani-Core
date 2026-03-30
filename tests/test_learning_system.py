"""
Tests for the learning system and src/core modules.

Covers:
- LearningEngine initialisation and basic step
- NeuralNetwork forward pass
- File existence and Python validity
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_CORE_DIR = os.path.join(ROOT, "src", "core")


def _import_learning_engine():
    if SRC_CORE_DIR not in sys.path:
        sys.path.insert(0, SRC_CORE_DIR)
    from learning_engine import LearningEngine  # noqa: PLC0415
    return LearningEngine


def _import_neural_network():
    if SRC_CORE_DIR not in sys.path:
        sys.path.insert(0, SRC_CORE_DIR)
    from neural_network import NeuralNetwork  # noqa: PLC0415
    return NeuralNetwork


# ---------------------------------------------------------------------------
# File presence
# ---------------------------------------------------------------------------

class TestSrcCoreFiles:
    """Verify src/core module files exist and are valid Python."""

    def test_learning_engine_file_exists(self):
        path = os.path.join(SRC_CORE_DIR, "learning_engine.py")
        assert os.path.isfile(path), "src/core/learning_engine.py must exist"

    def test_neural_network_file_exists(self):
        path = os.path.join(SRC_CORE_DIR, "neural_network.py")
        assert os.path.isfile(path), "src/core/neural_network.py must exist"

    def test_learning_engine_valid_python(self):
        path = os.path.join(SRC_CORE_DIR, "learning_engine.py")
        with open(path, "r") as fh:
            source = fh.read()
        compile(source, path, "exec")

    def test_neural_network_valid_python(self):
        path = os.path.join(SRC_CORE_DIR, "neural_network.py")
        with open(path, "r") as fh:
            source = fh.read()
        compile(source, path, "exec")


# ---------------------------------------------------------------------------
# NeuralNetwork
# ---------------------------------------------------------------------------

class TestNeuralNetwork:
    """Basic structural tests for the NeuralNetwork class."""

    def test_instantiation(self):
        NeuralNetwork = _import_neural_network()
        nn = NeuralNetwork(input_size=4, hidden_size=8, output_size=2)
        assert nn is not None

    def test_weight_shapes(self):
        NeuralNetwork = _import_neural_network()
        nn = NeuralNetwork(input_size=4, hidden_size=8, output_size=2)
        assert nn.W1.shape == (4, 8), "W1 should be (input_size, hidden_size)"
        assert nn.W2.shape == (8, 2), "W2 should be (hidden_size, output_size)"

    def test_forward_output_shape(self):
        import numpy as np  # noqa: PLC0415
        NeuralNetwork = _import_neural_network()
        nn = NeuralNetwork(input_size=4, hidden_size=8, output_size=2)
        x = np.random.rand(1, 4)
        output = nn.forward(x)
        assert output.shape == (1, 2), "Forward pass output should be (batch, output_size)"

    def test_forward_output_range(self):
        """Sigmoid activations should produce values in (0, 1)."""
        import numpy as np  # noqa: PLC0415
        NeuralNetwork = _import_neural_network()
        nn = NeuralNetwork(input_size=3, hidden_size=5, output_size=1)
        x = np.random.rand(5, 3)
        output = nn.forward(x)
        assert (output >= 0).all() and (output <= 1).all(), "Sigmoid output must be in [0, 1]"


# ---------------------------------------------------------------------------
# LearningEngine
# ---------------------------------------------------------------------------

class TestLearningEngine:
    """Basic structural tests for the LearningEngine class."""

    def test_instantiation(self):
        NeuralNetwork = _import_neural_network()
        LearningEngine = _import_learning_engine()
        model = NeuralNetwork(input_size=2, hidden_size=4, output_size=1)
        engine = LearningEngine(model=model, learning_rate=0.01)
        assert engine is not None

    def test_initial_learning_rate(self):
        NeuralNetwork = _import_neural_network()
        LearningEngine = _import_learning_engine()
        model = NeuralNetwork(input_size=2, hidden_size=4, output_size=1)
        engine = LearningEngine(model=model, learning_rate=0.05)
        assert engine.learning_rate == 0.05

    def test_history_initialized(self):
        NeuralNetwork = _import_neural_network()
        LearningEngine = _import_learning_engine()
        model = NeuralNetwork(input_size=2, hidden_size=4, output_size=1)
        engine = LearningEngine(model=model, learning_rate=0.01)
        assert hasattr(engine, "history"), "LearningEngine must have a history attribute"
        assert isinstance(engine.history, dict)
