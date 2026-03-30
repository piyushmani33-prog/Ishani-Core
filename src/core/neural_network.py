import numpy as np

class NeuralNetwork:
    def __init__(self, input_size, hidden_size, output_size):
        # Initialize weights and biases
        self.W1 = np.random.rand(input_size, hidden_size)
        self.b1 = np.zeros((1, hidden_size))
        self.W2 = np.random.rand(hidden_size, output_size)
        self.b2 = np.zeros((1, output_size))

    def forward(self, X):
        # Forward propagation: compute output
        self.z1 = np.dot(X, self.W1) + self.b1
        self.a1 = self.sigmoid(self.z1)
        self.z2 = np.dot(self.a1, self.W2) + self.b2
        output = self.sigmoid(self.z2)
        return output

    def backward(self, X, y, output):
        # Backward propagation: compute gradients
        output_error = output - y  # Gradient of loss w.r.t output
        output_delta = output_error * self.sigmoid_derivative(output)

        # Calculate hidden layer error
        hidden_layer_error = output_delta.dot(self.W2.T)
        hidden_layer_delta = hidden_layer_error * self.sigmoid_derivative(self.a1)

        # Update weights and biases here if needed, usually with a learning rate
        return output_delta, hidden_layer_delta

    def sigmoid(self, x):
        return 1 / (1 + np.exp(-x))

    def sigmoid_derivative(self, x):
        return x * (1 - x)