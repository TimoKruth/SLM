"""Bounded greedy generation with a fresh KV cache for each request."""
import time
import mlx.core as mx
import mlx.nn as nn


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



def greedy_generate(model, tokenizer, prompt, maximum=512, cached=True, deadline=None):
    """Keep complete prompts, never roll cached positions, and report exhausted context."""
    ids = tokenizer.encode('<bos><question>\n' + prompt + '\n<answer>\n').ids
    budget = max(0, min(maximum, model.config.context - len(ids)))
    stops = {tokenizer.token_to_id(t) for t in ('<eos>', '<bos>', '<pad>', '<question>')}
    output, cache = [], None
    reason = 'context_exceeded' if len(ids) >= model.config.context else 'token_limit'
    for _ in range(budget):
        if deadline is not None and time.time() >= deadline:
            reason = 'deadline'
            break
        if cached:
            tokens = ids if cache is None else ids[-1:]
            logits, cache = cached_forward(model, mx.array([tokens], dtype=mx.int32), cache)
        else:
            logits = model(mx.array([ids], dtype=mx.int32))
        token = int(mx.argmax(logits[:, -1, :], axis=-1).item())
        if token in stops:
            reason = 'special_token'
            break
        ids.append(token)
        output.append(token)
    return {'generated': tokenizer.decode(output), 'generated_tokens': len(output),
            'token_budget': budget, 'stop_reason': reason, 'cached': cached}
