
class CodegenConfig:
    # symbol to include, if empty, everything will be included
    symbols: list = []
    # regular expression for symbols to include
    expressions: list = []
    # verbose output
    verbose: bool = False
    # include source doxygen-style comments
    generate_comments: bool = False
    # include docstrings containing C prototype and source file location
    generate_docstrings: bool = False
    # include source file location in comments
    generate_locations: bool = False
    # do not include declaration defined outside of the source files
    filter_location: bool = True
    # dll to be loaded before all others (to resolve symbols)
    preloaded_dlls: list = []
    # kind of type descriptions to include
    types: list = []
    # the host's triplet
    local_platform_triple: str = None
    #
    known_symbols: dict = {}
    #
    searched_dlls: list = []
    # clang preprocessor options
    clang_opts: list = []

    def __init__(self):
        pass

    def parse_options(self, options):
        self.symbols = options.symbols
        self.expressions = options.expressions
        self.verbose = options.verbose
        self.generate_comments = options.generate_comments
        self.generate_docstrings = options.generate_docstrings
        self.generate_locations = options.generate_locations
        self.filter_location = not options.generate_includes
        self.preloaded_dlls = options.preload
        self.types = options.kind

    @property
    def cross_arch(self):
        """
        Is there a cross architecture option in clang_opts
        """
        return '-target' in ' '.join(self.clang_opts)

