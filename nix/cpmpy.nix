{ lib
, buildPythonPackage
, fetchFromGitHub
, setuptools
, wheel
, numpy
, ortools
}:

buildPythonPackage rec {
  pname = "cpmpy";
  version = "0.9.20";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "CPMpy";
    repo = "cpmpy";
    rev = "v${version}";
    hash = "sha256-2Yf63wEodFi/F6CpAo18D3WasaqopMdWxQRGoEetYcw=";
  };

  nativeBuildInputs = [
    setuptools
    wheel
  ];

  propagatedBuildInputs = [
    numpy
    ortools
    setuptools # for pkg_resources
  ];

  pythonImportsCheck = [ "cpmpy" ];

  meta = with lib; {
    description = "";
    homepage = "https://github.com/CPMpy/cpmpy";
    changelog = "https://github.com/CPMpy/cpmpy/blob/${src.rev}/changelog.md";
    license = licenses.asl20;
    maintainers = with maintainers; [ raitobezarius ];
  };
}
