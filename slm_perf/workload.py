"""Fixed-work optimizer step for monitoring-overhead calibration only."""
import mlx.core as mx
import mlx.optimizers as optim


def step(model, optimizer, grad_fn, x, y, mask, learning_rate):
    optimizer.learning_rate = learning_rate
    loss, grads = grad_fn(model, x, y, mask)
    grads, norm = optim.clip_grad_norm(grads, 1.0)
    optimizer.update(model, grads)
    mx.eval(model.parameters(), optimizer.state, loss, norm)
    return float(loss.item()), float(norm.item())
