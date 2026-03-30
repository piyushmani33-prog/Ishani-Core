import numpy as np
from typing import Tuple, Dict, List
import json
from pathlib import Path

class LearningEngine:
    def __init__(self, model, learning_rate: float = 0.001, adaptive: bool = True):
        """
        Initialize the learning engine.
        
        Args:
            model: Neural network model
            learning_rate: Initial learning rate
            adaptive: Whether to use adaptive learning rate
        """
        self.model = model
        self.initial_lr = learning_rate
        self.learning_rate = learning_rate
        self.adaptive = adaptive
        self.history = {
            'loss': [],
            'accuracy': [],
            'learning_rate': []
        }
        self.best_loss = float('inf')
        self.patience_counter = 0
    
    def calculate_loss(self, predictions: np.ndarray, targets: np.ndarray) -> float:
        """Calculate cross-entropy loss."""
        m = targets.shape[0]
        # Clip predictions to avoid log(0)
        eps = 1e-15
        predictions = np.clip(predictions, eps, 1 - eps)
        loss = -np.sum(targets * np.log(predictions) + (1 - targets) * np.log(1 - predictions)) / m
        return float(loss)
    
    def calculate_accuracy(self, predictions: np.ndarray, targets: np.ndarray) -> float:
        """Calculate classification accuracy."""
        pred_labels = (predictions > 0.5).astype(int)
        accuracy = np.mean(pred_labels == targets)
        return float(accuracy)
    
    def adaptive_learning_rate(self, epoch: int, total_epochs: int):
        """
        Adjust learning rate adaptively during training.
        Uses exponential decay.
        """
        if self.adaptive:
            decay_rate = 0.95
            self.learning_rate = self.initial_lr * (decay_rate ** (epoch / total_epochs * 10))
    
    def train_batch(self, X_batch: np.ndarray, y_batch: np.ndarray):
        """Train on a single batch."""
        predictions, _ = self.model.forward(X_batch)
        self.model.backward(X_batch, y_batch, learning_rate=self.learning_rate)
        return self.calculate_loss(predictions, y_batch)
    
    def train(self, 
              X_train: np.ndarray, 
              y_train: np.ndarray,
              X_val: np.ndarray = None,
              y_val: np.ndarray = None,
              epochs: int = 50,
              batch_size: int = 32,
              early_stopping_patience: int = 10,
              verbose: bool = True) -> Dict:
        """
        Train the model.
        
        Args:
            X_train: Training data
            y_train: Training labels
            X_val: Validation data (optional)
            y_val: Validation labels (optional)
            epochs: Number of training epochs
            batch_size: Batch size for training
            early_stopping_patience: Patience for early stopping
            verbose: Print training progress
            
        Returns:
            Training history
        """
        n_samples = X_train.shape[0]
        n_batches = (n_samples + batch_size - 1) // batch_size
        
        for epoch in range(epochs):
            # Adaptive learning rate
            self.adaptive_learning_rate(epoch, epochs)
            
            # Shuffle data
            indices = np.random.permutation(n_samples)
            X_shuffled = X_train[indices]
            y_shuffled = y_train[indices]
            
            # Train on batches
            epoch_loss = 0
            for batch_idx in range(n_batches):
                start_idx = batch_idx * batch_size
                end_idx = min((batch_idx + 1) * batch_size, n_samples)
                
                X_batch = X_shuffled[start_idx:end_idx]
                y_batch = y_shuffled[start_idx:end_idx]
                
                batch_loss = self.train_batch(X_batch, y_batch)
                epoch_loss += batch_loss
            
            epoch_loss /= n_batches
            
            # Calculate training metrics
            train_pred, _ = self.model.forward(X_train)
            train_accuracy = self.calculate_accuracy(train_pred, y_train)
            
            # Track metrics
            self.history['loss'].append(epoch_loss)
            self.history['accuracy'].append(train_accuracy)
            self.history['learning_rate'].append(self.learning_rate)
            
            # Validation
            if X_val is not None and y_val is not None:
                val_pred, _ = self.model.forward(X_val)
                val_loss = self.calculate_loss(val_pred, y_val)
                val_accuracy = self.calculate_accuracy(val_pred, y_val)
                
                # Early stopping
                if val_loss < self.best_loss:
                    self.best_loss = val_loss
                    self.patience_counter = 0
                else:
                    self.patience_counter += 1
                
                if self.patience_counter >= early_stopping_patience:
                    if verbose:
                        print(f"Early stopping at epoch {epoch}")
                    break
                
                if verbose and (epoch + 1) % max(1, epochs // 10) == 0:
                    print(f"Epoch {epoch+1}/{epochs}: Train Loss={epoch_loss:.4f}, "
                          f"Train Acc={train_accuracy:.2%}, Val Loss={val_loss:.4f}, "
                          f"Val Acc={val_accuracy:.2%}, LR={self.learning_rate:.6f}")
            else:
                if verbose and (epoch + 1) % max(1, epochs // 10) == 0:
                    print(f"Epoch {epoch+1}/{epochs}: Loss={epoch_loss:.4f}, "
                          f"Accuracy={train_accuracy:.2%}, LR={self.learning_rate:.6f}")
        
        return self.history
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict:
        """Evaluate model on test set."""
        predictions, _ = self.model.forward(X_test)
        loss = self.calculate_loss(predictions, y_test)
        accuracy = self.calculate_accuracy(predictions, y_test)
        
        return {
            'loss': loss,
            'accuracy': accuracy,
            'predictions': predictions
        }
    
    def get_training_summary(self) -> Dict:
        """Get summary of training progress."""
        return {
            'final_loss': float(self.history['loss'][-1]) if self.history['loss'] else None,
            'final_accuracy': float(self.history['accuracy'][-1]) if self.history['accuracy'] else None,
            'best_loss': float(self.best_loss),
            'loss_improvement': float((self.history['loss'][0] - self.history['loss'][-1]) / self.history['loss'][0] * 100) if self.history['loss'] else 0,
            'total_epochs': len(self.history['loss']),
            'final_learning_rate': float(self.history['learning_rate'][-1]) if self.history['learning_rate'] else None
        }