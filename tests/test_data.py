import numpy as np
import pandas as pd
import pytest

from delivery_ops.data import (parse_datetime, reconstruct_orders, build_rider_hours,
                               expand_events, weather_context, band, hourly_data)
from delivery_ops.config import STAGES


def source_order(order_id="1", **overrides):
    row = dict(id_pedido=order_id, id_comercio="merchant", id_repartidor="rider", vertical="restaurants",
               vehicle="bike", order_status="completed", fecha_creacion="2024-07-01 18:00:00",
               sent_to_vendor_at="2024-07-01 18:01:00", vendor_accepted_at="2024-07-01 18:06:00",
               rider_notified_at="2024-07-01 18:05:00", rider_accepted_at="2024-07-01 18:06:00",
               rider_at_pu="2024-07-01 18:09:00", rider_picked_up="2024-07-01 18:14:00",
               rider_at_do="2024-07-01 18:24:00", rider_droped_off="2024-07-01 18:26:00",
               tiempo_real=1440, tiempo_estimado=1200, cpo=100., undispatch_reason=None,
               pre_accept_undispatchs=0., post_accept_undispatchs=0., f0_=1000., pu_distance=500., do_distance=1500.)
    row.update(overrides)
    return row


def shift(rider, ident, start, end):
    a,b = pd.Timestamp(start), pd.Timestamp(end)
    return dict(shift_id=ident, rider_id=rider, fecha_inicio=a.normalize(), hora_inicio=a.time(),
                fecha_fin=b.normalize(), hora_fin=b.time())


def test_mixed_fractional_second_parser_preserves_both_formats():
    result = parse_datetime(pd.Series(["2024-07-01 12:00:00.123456", "2024-07-01 13:00:00", "bad"]))
    assert result.notna().tolist() == [True, True, False]
    assert result.iloc[0].microsecond == 123456


def test_cost_records_reconcile_without_inflating_demand():
    data = pd.DataFrame([source_order(), source_order(cpo=15., undispatch_reason="Reassigned"), source_order("2",cpo=200.)])
    o, records, qa = reconstruct_orders(data)
    assert len(o) == 2 and len(records) == 3
    assert o.set_index("id_pedido").loc["1","cpo_total"] == 115.
    assert o.cpo_total.sum() == data.cpo.sum()
    assert qa["unique_orders"] == 2


def test_missing_and_ambiguous_principal_rows_fail():
    with pytest.raises(ValueError, match="principal"):
        reconstruct_orders(pd.DataFrame([source_order(),source_order()]))
    with pytest.raises(ValueError, match="principal"):
        reconstruct_orders(pd.DataFrame([source_order(undispatch_reason="Only abort")]))


def test_parallel_merchant_branch_does_not_double_count_process():
    o,_,_ = reconstruct_orders(pd.DataFrame([source_order()]))
    assert o.process_eligible.all()
    assert o.t_espera_asignacion_min.iloc[0] == -1
    assert o[list(STAGES)].sum(axis=1).iloc[0] == 24
    assert o.t_total_from_created_min.iloc[0] == 26
    assert o.service_residual_seconds.iloc[0] == 0


def test_unknown_counter_is_not_zero_and_cancelled_not_late():
    o,_,_ = reconstruct_orders(pd.DataFrame([source_order(pre_accept_undispatchs=np.nan), source_order("2",order_status="cancelled")]))
    assert np.isnan(o.pre_any.iloc[0]) and np.isnan(o.any_undispatch.iloc[0])
    assert not o.service_eligible.iloc[1] and np.isnan(o.tardio.iloc[1])


def test_incomplete_and_negative_process_stages_are_ineligible():
    o,_,_ = reconstruct_orders(pd.DataFrame([source_order(rider_at_do=None), source_order("2", rider_at_pu="2024-07-01 18:04:00")]))
    assert not o.process_eligible.any()


def test_overlap_union_and_window_clipping_independent_expected_hours():
    data = pd.DataFrame([
        shift("a","1","2024-07-01 18:40","2024-07-01 21:10"),
        shift("a","2","2024-07-01 20:50","2024-07-01 21:30"),
        shift("a","3","2024-07-01 19:00","2024-07-01 19:20"),
        shift("b","4","2024-07-01 19:15","2024-07-01 19:45")])
    hours,_,_,qa = build_rider_hours(data,pd.Timestamp("2024-07-01 19:00"),pd.Timestamp("2024-07-01 21:00"))
    actual = hours.groupby("date_hour").rider_hours.sum()
    assert np.allclose(actual.to_numpy(), [1.5,1.0])
    assert hours.rider_hours.le(1).all()
    assert qa["overlapping_shift_rows"] == 2


def test_exact_midnight_end_does_not_add_next_hour():
    data = pd.DataFrame([shift("a","1","2024-07-01 23:30:00.100","2024-07-02 00:00:00")])
    hours,_,_,_ = build_rider_hours(data,pd.Timestamp("2024-07-01"),pd.Timestamp("2024-07-03"))
    assert len(hours) == 1
    assert abs(hours.rider_hours.sum() - (1800-.1)/3600) < 1e-9


def test_events_keep_holiday_and_match_and_deduplicate_exact_rows():
    raw = pd.DataFrame({"date":["2024-07-09", "2024-07-09 19:00", "2024-07-09 19:00", "2024-07-09 19:30"],
                        "event_type":["country_holiday","football_match","football_match","football_match"]})
    calendar=pd.DataFrame({"date_hour":pd.date_range("2024-07-09",periods=24,freq="h")})
    result,qa=expand_events(raw,calendar)
    row=result.set_index("date_hour").loc[pd.Timestamp("2024-07-09 19:00")]
    assert row.country_holiday and row.football_match
    assert row.football_match_count == 2
    assert qa["exact_duplicate_events"] == 1


def test_conflicting_weather_fails_instead_of_arbitrary_first():
    raw=pd.DataFrame({"date":["2024-07-01"]*2,"temperature":[10,12],"precip_mm":[0,0],"wind":[1,1],"condition":["Clear"]*2})
    with pytest.raises(ValueError,match="Conflicting"):
        weather_context(raw,pd.DataFrame({"date_hour":[pd.Timestamp("2024-07-01")]}))


def test_quantile_ties_and_missing_values_are_stable():
    result,cuts=band(pd.Series([1.,1.,1.,np.nan]))
    assert result.tolist()==["Low","Low","Low","Unknown"] and cuts==[1.,1.]


def test_hour_spine_keeps_demand_without_supply_and_supply_without_orders():
    orders,_,_=reconstruct_orders(pd.DataFrame([source_order()]))
    context=pd.DataFrame({"date_hour":pd.date_range("2024-07-01 18:00",periods=3,freq="h")})
    riders=pd.DataFrame({"rider_id":["r"],"date_hour":[pd.Timestamp("2024-07-01 19:00")],"rider_hours":[.5]})
    hours,_=hourly_data(orders,riders,context)
    assert len(hours)==3
    assert hours.pedidos.tolist()==[1,0,0]
    assert pd.isna(hours.utr_proxy.iloc[0])
    assert hours.utr_proxy.iloc[1]==0
    assert pd.isna(hours.rider_hours_total.iloc[2])
