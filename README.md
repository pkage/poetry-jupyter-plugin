# Poetry Jupyter plugin

## overview

This is a really simple plugin to allow you to install your
[Poetry](https://python-poetry.org) virtual environment as a
[Jupyter](https://jupyter.org) kernel. You may wish to do this to keep your
dependencies locked down for reproducible notebooks, or to set up a single
"data science" notebook for one-off calculations without fiddling about with
installing packages globally or dealing with `ipykernel` directly.

## getting started

Install the plugin with:

```sh
$ poetry self add poetry-jupyter-plugin
```

Then, from within your poetry project:

```sh
$ poetry install ipykernel -G dev
$ poetry jupyter install
```

Remove the kernelspec with:

```sh
$ poetry jupyter remove
```

### configuration

By default, the installed kernel will use the name of the project and a default
Poetry icon. To configure these options, add these lines to your `pyproject.toml`:

```toml
[tool.jupyter.kernel]
name = "my-cool-kernel"
display = "My cool kernel"
icon = "/path/to/icon.png"
```

## prior art

There are other projects in this space, notably Pathbird's [`poetry-kernel`].
`poetry-kernel` installs a single kernelspec globally which then patches the
virtualenv based on the specific project folder that you're running Jupyter in.
This has some pros and cons over this project.

Pros:

1. Single kernelspec, avoiding polluting the kernelspec list with lots of specs.
2. Easy context switching between projects.

Cons:

1. Notebooks have to be in the same folder (or a subfolder from) as the
   `pyproject.toml` folder.
2. Requires forwarding signals from the launcher into Jupyter, introducing a
   layer of complexity and is brittle to changes in Jupyter protocol/underlying
   OS.
3. Implicit dependency on `ipykernel`, and may fail to start without it.

In contrast, this project installs one kernelspec per virtualenv and leaves it
up to Jupyter to launch the kernel normally without interception. This design
decision also allows multiple projects to be based out of one kernel.
Additionally, the tool checks for the existence of `ipykernel` to make sure
that the kernel can be installed properly.

## who?

This was written by [patrick kage](//ka.ge).
