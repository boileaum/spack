# Copyright 2013-2022 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)
import os.path

import pytest

import spack.paths


@pytest.fixture()
def builder_test_repository():
    builder_test_path = os.path.join(spack.paths.repos_path, "builder.test")
    with spack.repo.use_repositories(builder_test_path) as mock_repo:
        yield mock_repo


@pytest.mark.parametrize(
    "spec_str,expected_values",
    [
        (
            "callbacks@2.0",
            [
                ("BEFORE_INSTALL_1_CALLED", "1"),
                ("BEFORE_INSTALL_2_CALLED", "1"),
                ("CALLBACKS_INSTALL_CALLED", "1"),
                ("AFTER_INSTALL_1_CALLED", "1"),
                ("TEST_VALUE", "3"),
                ("INSTALL_VALUE", "CALLBACKS"),
            ],
        ),
        # The last callback is conditional on "@1.0", check it's being executed
        (
            "callbacks@1.0",
            [
                ("BEFORE_INSTALL_1_CALLED", "1"),
                ("BEFORE_INSTALL_2_CALLED", "1"),
                ("CALLBACKS_INSTALL_CALLED", "1"),
                ("AFTER_INSTALL_1_CALLED", "1"),
                ("AFTER_INSTALL_2_CALLED", "1"),
                ("TEST_VALUE", "4"),
                ("INSTALL_VALUE", "CALLBACKS"),
            ],
        ),
        # The package below adds to "callbacks" using inheritance, test that using super()
        # works with builder hierarchies
        (
            "inheritance@1.0",
            [
                ("DERIVED_BEFORE_INSTALL_CALLED", "1"),
                ("BEFORE_INSTALL_1_CALLED", "1"),
                ("BEFORE_INSTALL_2_CALLED", "1"),
                ("CALLBACKS_INSTALL_CALLED", "1"),
                ("INHERITANCE_INSTALL_CALLED", "1"),
                ("AFTER_INSTALL_1_CALLED", "1"),
                ("AFTER_INSTALL_2_CALLED", "1"),
                ("TEST_VALUE", "4"),
                ("INSTALL_VALUE", "INHERITANCE"),
            ],
        ),
        # Generate custom phases using a GenericBuilder
        (
            "custom-phases",
            [
                ("CONFIGURE_CALLED", "1"),
                ("INSTALL_CALLED", "1"),
                ("LAST_PHASE", "INSTALL"),
            ],
        ),
        # Old-style package, with phase defined in base builder
        (
            "old-style-autotools@1.0",
            [
                ("AFTER_AUTORECONF_1_CALLED", "1"),
            ],
        ),
        (
            "old-style-autotools@2.0",
            [
                ("AFTER_AUTORECONF_2_CALLED", "1"),
            ],
        ),
        (
            "old-style-custom-phases",
            [
                ("AFTER_CONFIGURE_CALLED", "1"),
                ("TEST_VALUE", "0"),
            ],
        ),
    ],
)
@pytest.mark.usefixtures("builder_test_repository", "config")
@pytest.mark.disable_clean_stage_check
def test_callbacks_and_installation_procedure(spec_str, expected_values, working_env):
    """Test the correct execution of callbacks and installation procedures for packages."""
    s = spack.spec.Spec(spec_str).concretized()
    builder = spack.builder.create(s.package)
    for phase_fn in builder:
        phase_fn.execute()

    # Check calls have produced the expected side effects
    for var_name, expected in expected_values:
        assert os.environ[var_name] == expected, os.environ


@pytest.mark.usefixtures("builder_test_repository", "config")
@pytest.mark.parametrize(
    "spec_str,method_name,expected",
    [
        # Call a function defined on the package, which calls the same function defined
        # on the super(builder)
        ("old-style-autotools", "configure_args", ["--with-foo"]),
        # Call a function defined on the package, which calls the same function defined on the
        # super(pkg), which calls the same function defined in the super(builder)
        ("old-style-derived", "configure_args", ["--with-bar", "--with-foo"]),
    ],
)
def test_old_style_compatibility_with_super(spec_str, method_name, expected):
    s = spack.spec.Spec(spec_str).concretized()
    builder = spack.builder.create(s.package)
    value = getattr(builder, method_name)()
    assert value == expected
