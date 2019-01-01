**[Increment / decrement path](inc.patch)**

A path that add an increment / decrement statements. Usage:

```python
variable ++
variable --
```

**[Until path](until.patch)**

Usage:
```python
until variable == 0:
    variable -= 1
```

**[New opcode path](new_opcode.patch)**

This patch combines these two opcodes

```python
LOAD_FAST
LOAD_CONST
```

into a single opcode:

```python
LOAD_OTUS
```

**To apply the patch you should run:**

`git apply <name>.patch`
