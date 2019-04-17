from conans import ConanFile, CMake, tools
import os


class CEFConan(ConanFile):
    name = "cef"
    version = "73.1.12"
    version_full = "73.1.12+gee4b49f+chromium-73.0.3683.75"
    description = "The Chromium Embedded Framework (CEF) is an open source framework for embedding a web browser engine which is based on the Chromium core"
    topics = ("conan", "cef", "chromium", "chromium-embedded-framework")
    url = "https://github.com/bincrafters/conan-cef"
    homepage = "https://bitbucket.org/chromiumembedded/cef"
    author = "Bincrafters <bincrafters@gmail.com>"
    license = "BSD-3Clause"
    exports = ["LICENSE.md"]
    exports_sources = ["CMakeLists.txt"]
    generators = "cmake"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "use_sandbox": [True, False],
        "debug_info_flag_vs": ["-Zi", "-Z7"]
    }
    default_options = {
        'use_sandbox': False,
        'debug_info_flag_vs': '-Z7'
    }

    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    def get_cef_distribution_name(self):
        platform = ""
        if self.settings.os == "Windows":
            platform = "windows"
        if self.settings.os == "Macos":
            platform = "macosx"
        if self.settings.os == "Linux":
            platform = "linux"
        if self.settings.arch == "x86":
            platform += "32"
        else:
            platform += "64"
        return "cef_binary_%s_%s" % (self.version_full, platform)

    # def config(self):
        # if self.settings.os == "Windows" and self.settings.compiler == "Visual Studio" and self.settings.compiler.version != "14":
            # self.options.remove("use_sandbox") # it requires to be built with that exact version for sandbox support

    def _download(self):
        self.output.info("Downloading CEF prebuilts from opensource.spotify.com/cefbuilds/index.html")

        cef_download_filename ="{}.tar.bz2".format(self.get_cef_distribution_name()).replace("+", "%2B")
        archive_url = "http://opensource.spotify.com/cefbuilds/{}".format(cef_download_filename)
        tools.get(archive_url)
        os.rename(self.get_cef_distribution_name(), self._source_subfolder)
        insert_position = "project(cef)"
        tools.replace_in_file("{}/CMakeLists.txt".format(self._source_subfolder),
            insert_position, insert_position + '''
include(${CMAKE_BINARY_DIR}/../conanbuildinfo.cmake)
conan_basic_setup()''')

    def system_requirements(self):
        if self.settings.os == "Linux" and tools.os_info.is_linux:
            if tools.os_info.with_apt:
                installer = tools.SystemPackageTool()
                if self.settings.arch == "x86":
                    arch_suffix = ':i386'
                elif self.settings.arch == "x86_64":
                    arch_suffix = ':amd64'

                packages = ['libpangocairo-1.0-0{}'.format(arch_suffix)]
                packages.append('libxcomposite1{}'.format(arch_suffix))
                packages.append('libxrandr2{}'.format(arch_suffix))
                packages.append('libxcursor1{}'.format(arch_suffix))
                packages.append('libatk1.0-0{}'.format(arch_suffix))
                packages.append('libcups2{}'.format(arch_suffix))
                packages.append('libnss3{}'.format(arch_suffix))
                packages.append('libgconf-2-4{}'.format(arch_suffix))
                packages.append('libxss1{}'.format(arch_suffix))
                packages.append('libasound2{}'.format(arch_suffix))
                packages.append('libxtst6{}'.format(arch_suffix))
                packages.append('libgtk2.0-dev{}'.format(arch_suffix))
                packages.append('libgdk-pixbuf2.0-dev{}'.format(arch_suffix))
                packages.append('freeglut3-dev{}'.format(arch_suffix))

                for package in packages:
                    installer.install(package)

    def _configure_cmake(self):
        cmake = CMake(self)
        cmake.definitions["USE_SANDBOX"] = "ON" if self.options.use_sandbox else "OFF"
        if self.settings.compiler == "Visual Studio":
            cmake.definitions["CEF_RUNTIME_LIBRARY_FLAG"] = "/" + str(self.settings.compiler.runtime)
            cmake.definitions["CEF_DEBUG_INFO_FLAG"] = self.options.debug_info_flag_vs

        cmake.configure(source_folder=self._source_subfolder, build_folder=self._build_subfolder)
        return cmake

    def build(self):
        self._download()
        cmake = self._configure_cmake()
        cmake.build(target="libcef_dll_wrapper")

    def package(self):
        # Copy headers
        self.copy('*', dst='include/include', src='{}/include'.format(self._source_subfolder))

        # Copy all stuff from the Debug/Release folders in the downloaded cef bundle:
        dis_folder = "{}/{}".format(self._source_subfolder, self.settings.build_type)
        res_folder = "{}/Resources".format(self._source_subfolder)
        self.copy("*.*", dst="bin", src=res_folder)

        if self.settings.os == "Linux":
            # CEF binaries: (Taken from cmake/cef_variables)
            self.copy("libcef.so", dst="lib", src=dis_folder, keep_path=False)
            self.copy("natives_blob.bin", dst="bin", src=dis_folder, keep_path=False)
            self.copy("snapshot_blob.bin", dst="bin", src=dis_folder, keep_path=False)
            if self.options.use_sandbox:
                self.copy("chrome-sandbox", dst="bin", src=dis_folder, keep_path=False)
            self.copy("*cef_dll_wrapper.a", dst="lib", keep_path=False)
        elif self.settings.os == "Macos":
            # CEF binaries: (Taken from cmake/cef_variables)
            self.copy("Chromium Embedded Framework.framework/*", src=dis_folder, symlinks=True)
            if self.options.use_sandbox:
                self.copy("cef-sandbox.a", dst="bin", src=dis_folder, keep_path=False)
            self.copy("*cef_dll_wrapper.a", dst="lib", keep_path=False)
        elif self.settings.os == "Windows":
            self.copy("*.dll", dst="bin", src=dis_folder)
            self.copy("*.lib", dst="lib", src=dis_folder)
            self.copy("*.bin", dst="bin", src=dis_folder)
            self.copy("*.lib", dst="lib", src="{}/lib".format(self._build_subfolder))

    def package_info(self):
        if self.settings.os == "Macos":
            self.cpp_info.libs.append("cef_dll_wrapper")
        elif self.settings.compiler == "Visual Studio":
            self.cpp_info.libs = ["libcef_dll_wrapper", "libcef"]
        else:
            self.cpp_info.libs = ["cef_dll_wrapper", "cef"]
            self.cpp_info.defines += ["_FILE_OFFSET_BITS=64"]

        if self.options.use_sandbox:
            if self.settings.os == "Windows":
                self.cpp_info.libs += ["cef_sandbox", "dbghelp", "psapi", "version", "winmm"]
            self.cpp_info.defines += ["USE_SANDBOX", "CEF_USE_SANDBOX", "PSAPI_VERSION=1"]
        if self.settings.os == "Windows":
            self.cpp_info.libs += ["glu32", "opengl32", "comctl32", "rpcrt4", "shlwapi", "ws2_32"]
