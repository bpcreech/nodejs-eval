# NodeJS Eval

Evaluate arbitrary JavaScript from Python, using a NodeJS sidecar process.

This combines:

- The Python [`nodejs-bin`](https://pypi.org/project/nodejs-bin/) project, which
  bundles NodeJS (with `npm` and `npx`) into a PyPI package, and
- The JavaScript/TypeScript
  [`http-eval`](https://www.npmjs.com/package/http-eval) project, which runs a
  JavaScript evaluation server on a Unix domain socket.

[![PyPI - Version](https://img.shields.io/pypi/v/nodejs-eval.svg)](https://pypi.org/project/nodejs-eval)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/nodejs-eval.svg)](https://pypi.org/project/nodejs-eval)

______________________________________________________________________

**Table of Contents**

- [Installation](#installation)
- [License](#license)
- [Usage instructions](#usage-instructions)

## Installation

```console
pip install nodejs-eval
```

## License

`nodejs-eval` is distributed under the terms of the
[MIT](https://spdx.org/licenses/MIT.html) license.

## Usage instructions

### Basic synchronous call

JavaScript code is evaluated as a function body within a synchronous or
asynchronous JavaScript function, within an ECMAScript module.

Note that the NodeJS evaluator always only supports `async` mode on the Python
side. However, the supplied JavaScript code can be either sync or async.

```python
    from nodejs_eval.eval import evaluator

    async with evaluator() as e:
        result = await e.run("return 6*7;")
        assert result == 42
```

### Basic asynchronous call

```python
    from nodejs_eval.eval import evaluator

    async with evaluator() as e:
        result = await e.run_async(
            """
await new Promise(r => setTimeout(r, 2000));
return 6*7;
""")
        assert result == 42
```

### Storing state on `this`

Evaluations run with a consistent JavaScript `this` context, so state can be
stored on it:

```python
    from nodejs_eval.eval import evaluator

    async with evaluator() as e:
        await e.run("this.x = 6*7;")
        result = await e.run("return this.x;")
        assert result == 42
```

### Import using dynamic `await import()`

Because code is executed within an ECMAScript module, you can use
[the dynamic async `import()`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/import)
to import other modules.

This is easiest done in `async` mode:

```python
    from nodejs_eval.eval import evaluator

    async with evaluator() as e:
        result = await e.run_async(
            """
const os = await import("os");
return os.cpus();
"""
        )
        assert len(result) > 0
```
