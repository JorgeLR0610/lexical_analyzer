"""Instruction-level backward liveness and deterministic bounded coloring."""
REGISTERS = ('rbx', 'r12', 'r13', 'r14', 'r15')


def allocate(quads, params, symbols, function):
    local = {n for n, s in symbols.items() if s['function'] == function}
    labels = {q.result: i for i, q in enumerate(quads) if q.op == 'label'}
    uses = []
    defs = []
    successors = []
    for i, q in enumerate(quads):
        args = [q.arg1] if q.op in ('param', 'print', 'return', 'ifFalse', 'ifTrue') else ([] if q.op in ('call', 'label', 'goto', 'newline') else [q.arg1, q.arg2])
        uses.append(set(args) & local)
        defs.append(({q.result} & local) if q.op not in ('label', 'goto', 'ifFalse', 'ifTrue', 'print') else set())
        nxt = [] if q.op in ('goto', 'return') else ([i + 1] if i + 1 < len(quads) else [])
        if q.op in ('goto', 'ifFalse', 'ifTrue'):
            nxt.append(labels[q.result])
        successors.append(nxt)
    ins = [set() for _ in quads]
    outs = [set() for _ in quads]
    changed = True
    while changed:
        changed = False
        for i in reversed(range(len(quads))):
            out = set().union(*(ins[j] for j in successors[i]))
            incoming = uses[i] | (out - defs[i])
            if incoming != ins[i] or out != outs[i]:
                changed = True
            ins[i], outs[i] = incoming, out
    active = set(params) | set().union(*uses, *defs)
    graph = {n: set() for n in active}

    def clique(nodes):
        for a in nodes:
            graph[a].update(nodes - {a})

    clique(set(params))
    for i in range(len(quads)):
        clique(ins[i])
        clique(outs[i] | defs[i])
    locations = {}
    spills = 0
    while len(locations) < len(graph):
        pending = set(graph) - locations.keys()
        n = max(pending, key=lambda n: (len({locations[x] for x in graph[n] if x in locations}), len(graph[n]), n))
        occupied = {locations[x] for x in graph[n] if x in locations}
        reg = next((r for r in REGISTERS if r not in occupied), None)
        if reg:
            locations[n] = reg
        else:
            spills += 1
            locations[n] = f'QWORD PTR [rbp-{40 + 8 * spills}]'
    return locations, spills, [(a, b) for a in sorted(graph) for b in sorted(graph[a]) if a < b]
