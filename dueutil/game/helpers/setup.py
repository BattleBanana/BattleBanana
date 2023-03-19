# cython: language_level=3

if __name__ == "__main__":
    from Cython.Build import cythonize
    from setuptools import Extension, setup

    ext = Extension(name="speedup", sources=["speedup.pyx"])
    setup(ext_modules=cythonize(ext, compiler_directives={"language_level": 3, "infer_types": True}))
