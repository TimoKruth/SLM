"""Isolated candidates. The live training and evaluation modules do not import this file."""
import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from slm.model import loss_fn


def cached_forward(model,tokens,cache=None):
    layers=len(model.blocks)
    cache=[None]*layers if cache is None else cache
    if len(cache)!=layers:raise ValueError('Cache layer count mismatch')
    offset=0 if cache[0] is None else cache[0][0].shape[2]
    if tokens.shape[1]==0 or offset+tokens.shape[1]>model.config.context:
        raise ValueError('Empty input or context budget exceeded')
    x=model.embedding(tokens);updated=[]
    for block,prior in zip(model.blocks,cache):
        h=block.norm1(x);b,t,d=h.shape;attn=block.attn
        q,k,v=mx.split(attn.qkv(h),3,axis=-1)
        q,k,v=[z.reshape(b,t,attn.heads,attn.head_dim).transpose(0,2,1,3) for z in (q,k,v)]
        q,k=attn.rope(q,offset=offset),attn.rope(k,offset=offset)
        if prior is not None:
            if prior[0].shape[2]!=offset:raise ValueError('Inconsistent layer offsets')
            k=mx.concatenate([prior[0],k],axis=2);v=mx.concatenate([prior[1],v],axis=2)
        updated.append((k,v))
        mask=None
        if t>1:
            # Causal mask aligned to the absolute position when appending a chunk.
            mask=mx.where(mx.arange(offset+t)[None,:]<=offset+mx.arange(t)[:,None],0.,-float('inf'))
        a=mx.fast.scaled_dot_product_attention(q,k,v,scale=attn.head_dim**-.5,mask=mask)
        x=x+attn.out(a.transpose(0,2,1,3).reshape(b,t,d))
        h=block.norm2(x);x=x+block.down(nn.silu(block.gate(h))*block.up(h))
    return model.embedding.as_linear(model.norm(x)),updated


def tokens_greedy(model,ids,count,cached=False):
    if len(ids)+count>model.config.context:raise ValueError('Generation exceeds context budget')
    ids=list(ids);out=[];cache=None
    for _ in range(count):
        if cached:
            inputs=ids if cache is None else ids[-1:]
            logits,cache=cached_forward(model,mx.array([inputs],dtype=mx.int32),cache)
            mx.eval(cache)
        else:logits=model(mx.array([ids],dtype=mx.int32))
        token=int(mx.argmax(logits[:,-1,:],axis=-1).item());ids.append(token);out.append(token)
    return out


def make_training_step(model,compiled=False):
    opt=optim.AdamW(learning_rate=3e-4,betas=[.9,.95],weight_decay=.1,bias_correction=True)
    opt.init(model.trainable_parameters())
    state=[model.state,opt.state]
    grad=nn.value_and_grad(model,loss_fn)
    def update(x,y,mask,learning_rate):
        opt.learning_rate=learning_rate
        loss,grads=grad(model,x,y,mask)
        grads,norm=optim.clip_grad_norm(grads,1.)
        opt.update(model,grads)
        return loss,norm
    fn=mx.compile(update,inputs=state,outputs=state) if compiled else update
    return fn,opt,state
