import xarray as xr
import numpy as np
from numpy.testing import assert_allclose

from xyzpy.gen.case_runner import (
    case_runner,
    case_runner_to_ds,
    case_runner_to_df,
    find_missing_cases,
)
from . import (
    foo3_scalar,
    foo3_float_bool,
    foo2_array,
    foo2_array_array,
    foo2_zarray1_zarray2,
)


# --------------------------------------------------------------------------- #
# CASE_RUNNER tests                                                           #
# --------------------------------------------------------------------------- #

class TestCaseRunner:
    def test_seq(self):
        cases = ((1, 10, 100),
                 (2, 20, 200),
                 (3, 30, 300))
        xs = case_runner(foo3_scalar, ('a', 'b', 'c'), cases, verbosity=0)
        assert xs == (111, 222, 333)

    def test_progbar(self):
        cases = ((1, 10, 100),
                 (2, 20, 200),
                 (3, 30, 300))
        xs = case_runner(foo3_scalar, ('a', 'b', 'c'), cases, verbosity=2)
        assert xs == (111, 222, 333)

    def test_constants(self):
        cases = ((1,),
                 (2,),
                 (3,))
        xs = case_runner(foo3_scalar, ('a', 'b', 'c'), cases,
                         constants={'b': 10, 'c': 100})
        assert xs == (111, 112, 113)

    def test_parallel(self):
        cases = ((1, 10, 100),
                 (2, 20, 200),
                 (3, 30, 300))
        xs = case_runner(foo3_scalar, ('a', 'b', 'c'), cases, num_workers=1)
        assert xs == (111, 222, 333)

    def test_split(self):
        cases = ((1, 10, 100),
                 (2, 20, 200),
                 (3, 30, 300))
        a, b = case_runner(foo3_float_bool, ('a', 'b', 'c'), cases, split=True)
        assert a == (111, 222, 333)
        assert b == (False, True, False)

    def test_single_args(self):
        cases = (1, 2, 3)
        xs = case_runner(foo3_scalar, 'a', cases,
                         constants={'b': 10, 'c': 100})
        assert xs == (111, 112, 113)


class TestCaseRunnerToDS:
    def test_single(self):
        cases = [(1, 20, 300),
                 (3, 20, 100)]
        ds = case_runner_to_ds(foo3_scalar, ['a', 'b', 'c'], cases=cases,
                               var_names='sum')
        assert_allclose(ds['a'].data, [1, 3])
        assert_allclose(ds['b'].data, [20])
        assert_allclose(ds['c'].data, [100, 300])
        assert ds['sum'].loc[{'a': 1, 'b': 20, 'c': 300}].data == 321
        assert ds['sum'].loc[{'a': 3, 'b': 20, 'c': 100}].data == 123
        assert ds['sum'].loc[{'a': 1, 'b': 20, 'c': 100}].isnull()
        assert ds['sum'].loc[{'a': 3, 'b': 20, 'c': 300}].isnull()

    def test_single_dict_cases(self):
        cases = [{'a': 1, 'b': 20, 'c': 300}, {'a': 3, 'b': 20, 'c': 100}]
        ds = case_runner_to_ds(foo3_scalar, None, cases=cases, var_names='sum')
        assert_allclose(ds['a'].data, [1, 3])
        assert_allclose(ds['b'].data, [20])
        assert_allclose(ds['c'].data, [100, 300])
        assert ds['sum'].loc[{'a': 1, 'b': 20, 'c': 300}].data == 321
        assert ds['sum'].loc[{'a': 3, 'b': 20, 'c': 100}].data == 123
        assert ds['sum'].loc[{'a': 1, 'b': 20, 'c': 100}].isnull()
        assert ds['sum'].loc[{'a': 3, 'b': 20, 'c': 300}].isnull()

    def test_multires(self):
        cases = [(1, 20, 300),
                 (3, 20, 100)]
        ds = case_runner_to_ds(foo3_float_bool,
                               fn_args=['a', 'b', 'c'],
                               cases=cases,
                               var_names=['sum', 'a_even'])
        assert_allclose(ds['a'].data, [1, 3])
        assert_allclose(ds['b'].data, [20])
        assert_allclose(ds['c'].data, [100, 300])
        assert ds['sum'].loc[{'a': 1, 'b': 20, 'c': 300}].data == 321
        assert ds['sum'].loc[{'a': 3, 'b': 20, 'c': 100}].data == 123
        assert ds['sum'].loc[{'a': 1, 'b': 20, 'c': 100}].isnull()
        assert ds['sum'].loc[{'a': 3, 'b': 20, 'c': 300}].isnull()
        assert ds['a_even'].data.dtype == object
        assert bool(ds['a_even'].sel(a=1, b=20, c=300).data) is False
        assert bool(ds['a_even'].sel(a=3, b=20, c=100).data) is False
        assert ds['a_even'].loc[{'a': 1, 'b': 20, 'c': 100}].isnull()
        assert ds['a_even'].loc[{'a': 3, 'b': 20, 'c': 300}].isnull()

    def test_array_return(self):
        ds = case_runner_to_ds(fn=foo2_array, fn_args=['a', 'b'],
                               cases=[(2, 30), (4, 50)],
                               var_names='x',
                               var_dims=['time'],
                               var_coords={'time': np.arange(10) / 10})
        assert ds.x.data.dtype == float
        assert ds.x.sel(a=2, b=50, time=0.7).isnull()
        assert ds.x.sel(a=4, b=50, time=0.3).data == 54.3

    def test_multi_array_return(self):
        ds = case_runner_to_ds(fn=foo2_array_array, fn_args=['a', 'b'],
                               cases=[(2, 30), (4, 50)],
                               var_names=['x', 'y'],
                               var_dims={('x', 'y'): 'time'},
                               var_coords={'time': ['a', 'b', 'c', 'd', 'e']})
        assert ds['time'].data.dtype != object
        assert_allclose(ds['x'].sel(a=4, b=50).data,
                        [50, 54, 58, 62, 66])
        assert_allclose(ds['y'].sel(a=4, b=50).data,
                        [50, 46, 42, 38, 34])

    def test_align_and_fillna_int(self):
        ds1 = case_runner_to_ds(foo2_array_array, fn_args=['a', 'b'],
                                cases=[(1, 10), (2, 20)],
                                var_names=['x', 'y'],
                                var_dims={('x', 'y'): 'time'},
                                var_coords={'time':
                                            ['a', 'b', 'c', 'd', 'e']})
        ds2 = case_runner_to_ds(foo2_array_array, fn_args=['a', 'b'],
                                cases=[(2, 10), (1, 20)],
                                var_names=['x', 'y'],
                                var_dims={('x', 'y'): 'time'},
                                var_coords={'time':
                                            ['a', 'b', 'c', 'd', 'e']})
        assert not np.logical_not(ds1['x'].isnull()).all()
        assert not np.logical_not(ds1['y'].isnull()).all()
        assert not np.logical_not(ds2['x'].isnull()).all()
        assert not np.logical_not(ds2['y'].isnull()).all()
        ds1, ds2 = xr.align(ds1, ds2, join='outer')
        fds = ds1.fillna(ds2)
        assert np.logical_not(fds['x'].isnull()).all()
        assert np.logical_not(fds['y'].isnull()).all()

    def test_align_and_fillna_complex(self):
        ds1 = case_runner_to_ds(foo2_zarray1_zarray2, fn_args=['a', 'b'],
                                cases=[(1j, 10), (2j, 20)],
                                var_names=['x', 'y'],
                                var_dims={('x', 'y'): 'time'},
                                var_coords={'time':
                                            ['a', 'b', 'c', 'd', 'e']})
        ds2 = case_runner_to_ds(foo2_zarray1_zarray2, fn_args=['a', 'b'],
                                cases=[(2j, 10), (1j, 20)],
                                var_names=['x', 'y'],
                                var_dims={('x', 'y'): 'time'},
                                var_coords={'time':
                                            ['a', 'b', 'c', 'd', 'e']})
        assert not np.logical_not(np.isnan(ds1['x'].data)).all()
        assert not np.logical_not(np.isnan(ds1['y'].data)).all()
        assert not np.logical_not(np.isnan(ds2['x'].data)).all()
        assert not np.logical_not(np.isnan(ds2['y'].data)).all()
        assert all(t == complex for t in (ds1.x.dtype, ds2.x.dtype,
                                          ds1.y.dtype, ds2.y.dtype))
        assert ds1.y.dtype == complex
        assert ds2.y.dtype == complex
        ds1, ds2 = xr.align(ds1, ds2, join='outer')
        fds = ds1.fillna(ds2)
        assert np.logical_not(np.isnan(fds['x'].data)).all()
        assert np.logical_not(np.isnan(fds['y'].data)).all()


class TestCaseRunnerToDF:

    def test_single_arg(self):

        df = case_runner_to_df(
            fn=foo3_scalar,
            fn_args=['a', 'b', 'c'],
            cases=[(1, 10, 100), (2, 20, 200)],
            var_names='x',
        )
        assert len(df) == 2
        assert df.columns.tolist() == ['a', 'b', 'c', 'x']
        assert 'int' in df.x.dtype.name


# --------------------------------------------------------------------------- #
# Finding and filling missing data                                            #
# --------------------------------------------------------------------------- #

class TestFindMissingCases:
    def test_simple(self):
        ds = xr.Dataset(coords={'a': [1, 2, 3], 'b': [40, 50]})
        ds['x'] = (('a', 'b'), np.array([[0.1, np.nan],
                                         [np.nan, 0.2],
                                         [np.nan, np.nan]]))
        # Target cases and settings
        t_cases = ((1, 50), (2, 40), (3, 40), (3, 50))
        t_configs = tuple(dict(zip(['a', 'b'], t_case)) for t_case in t_cases)
        # Missing cases and settings
        m_args, m_cases = find_missing_cases(ds)
        m_configs = tuple(dict(zip(m_args, m_case)) for m_case in m_cases)
        # Assert same set of coordinates
        assert all(t_config in m_configs for t_config in t_configs)
        assert all(m_config in t_configs for m_config in m_configs)

    def test_multires(self):
        ds = xr.Dataset(coords={'a': [1, 2, 3], 'b': [40, 50]})
        ds['x'] = (('a', 'b'), np.array([[0.1, np.nan],
                                         [np.nan, 0.2],
                                         [np.nan, np.nan]]))
        ds['y'] = (('a', 'b'), np.array([['a', None],
                                         [None, 'b'],
                                         [None, None]]))
        # Target cases and settings
        t_cases = ((1, 50), (2, 40), (3, 40), (3, 50))
        t_configs = tuple(dict(zip(['a', 'b'], t_case)) for t_case in t_cases)
        # Missing cases and settings
        m_args, m_cases = find_missing_cases(ds)
        m_configs = tuple(dict(zip(m_args, m_case)) for m_case in m_cases)
        # Assert same set of coordinates
        assert set(m_args) == {'a', 'b'}
        assert all(t_config in m_configs for t_config in t_configs)
        assert all(m_config in t_configs for m_config in m_configs)

    def test_var_dims_leave(self):
        ds = xr.Dataset(coords={'a': [1, 2, 3], 'b': [40, 50],
                                't': [0.1, 0.2, 0.3]})
        ds['x'] = (('a', 'b'), np.array([[0.1, np.nan],
                                         [np.nan, 0.2],
                                         [np.nan, np.nan]]))
        ds['y'] = (('a', 'b', 't'), np.array([[[0.2] * 3, [np.nan] * 3],
                                              [[np.nan] * 3, [0.4] * 3],
                                              [[np.nan] * 3, [np.nan] * 3]]))
        # Target cases and settings
        t_cases = ((1, 50), (2, 40), (3, 40), (3, 50))
        t_configs = tuple(dict(zip(['a', 'b'], t_case)) for t_case in t_cases)
        # Missing cases and settings
        m_args, m_cases = find_missing_cases(ds, ignore_dims='t')
        m_configs = tuple(dict(zip(m_args, m_case)) for m_case in m_cases)
        # Assert same set of coordinates
        assert set(m_args) == {'a', 'b'}
        assert all(t_config in m_configs for t_config in t_configs)
        assert all(m_config in t_configs for m_config in m_configs)
