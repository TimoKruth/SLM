"""Validated execution optimizations; model/checkpoint representation stays unchanged."""
import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from .model import loss_fn


def make_training_step(model, optimizer, compiled=True):
    """Capture mutable model/Adam state, with learning rate supplied on every call."""
    optimizer.init(model.trainable_parameters())
    state = [model.state, optimizer.state]
    grad_fn = nn.value_and_grad(model, loss_fn)

    def update(x, y, mask, learning_rate):
        optimizer.learning_rate = learning_rate
        loss, grads = grad_fn(model, x, y, mask)
        grads, norm = optim.clip_grad_norm(grads, 1.0)
        optimizer.update(model, grads)
        return loss, norm

    return mx.compile(update, inputs=state, outputs=state) if compiled else update
