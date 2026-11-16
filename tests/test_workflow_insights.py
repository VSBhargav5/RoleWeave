from contextlib import closing
from datetime import date
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from job_store import JobStore
from workflow_insights import insights, records


class InsightsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=JobStore(Path(self.temp.name)/'jobs.db')
        payload=(Path(__file__).parents[1]/'examples/synthetic.json').read_bytes()
        self.one=self.store.save(payload,'First review','Synthetic Co')
        other=json.loads(payload);other['posting']+=' Second synthetic review, same employer.';other['market']='relocation'
        self.two=self.store.save(json.dumps(other).encode(),'Second review','Synthetic Co')
        self.today=date(2028,2,29)

    def event(self,identifier,stage,due='',stamp='2028-02-26T10:00:00+00:00'):
        event=self.store.record_application(identifier,stage,'Private note excluded from analytics',due)
        with closing(sqlite3.connect(self.store.path)) as db,db:db.execute('UPDATE application_events SET recorded_at=? WHERE id=?',(stamp,event['id']))

    def view(self,**kwargs):return insights(self.store,today=self.today,month=kwargs.pop('month','2028-02'),**kwargs)

    def test_empty_and_unsaved_history_current_and_observed_defaults(self):
        data=self.view();self.assertEqual(data['reviews'],2)
        self.assertEqual(dict((r['stage'],r['count']) for r in data['current'])['saved'],2)
        self.assertEqual(sum(w['count'] for w in data['weeks']),0);self.assertEqual(data['month_due'],0)
        empty=JobStore(Path(self.temp.name)/'empty.db');self.assertEqual(insights(empty,today=self.today)['reviews'],0)

    def test_current_correction_does_not_erase_observed_history_or_infer_stages(self):
        self.event(self.one,'applied');self.event(self.one,'interview');self.event(self.one,'saved')
        self.event(self.two,'offer')
        data=self.view();current={r['stage']:r['count'] for r in data['current']};ever={r['stage']:r['count'] for r in data['observed']}
        self.assertEqual(current['saved'],1);self.assertEqual(current['offer'],1)
        self.assertEqual(ever['applied'],1);self.assertEqual(ever['interview'],1);self.assertEqual(ever['offer'],1)
        self.assertEqual(sum(w['count'] for w in data['weeks']),1)

    def test_first_applied_per_review_utc_boundary_and_repeated_updates(self):
        self.event(self.one,'applied',stamp='2028-02-27T23:30:00-02:00')
        self.event(self.one,'applied',stamp='2028-02-29T10:00:00+00:00')
        data=self.view();self.assertEqual(data['weeks'][-1]['start'],'2028-02-28');self.assertEqual(data['weeks'][-1]['count'],1)
        self.assertEqual(sum(w['count'] for w in data['weeks']),1)

    def test_market_filters_every_chart_and_calendar_without_cross_market_state(self):
        self.event(self.one,'applied','2028-02-29');self.event(self.two,'interview','2028-02-29')
        india=self.view(market='india_remote');away=self.view(market='relocation')
        self.assertEqual(india['reviews'],1);self.assertEqual(away['reviews'],1)
        self.assertEqual(sum(w['count'] for w in away['weeks']),0)
        self.assertEqual([i['id'] for d in india['days'] for i in d['items']],[self.one])
        self.assertEqual([i['id'] for d in away['days'] for i in d['items']],[self.two])

    def test_leap_month_monday_grid_and_adjacent_month_membership(self):
        data=self.view();self.assertEqual(len(data['days']),42);self.assertEqual(date.fromisoformat(data['days'][0]['date']).weekday(),0)
        self.assertEqual(sum(d['in_month'] for d in data['days']),29)
        leap=[d for d in data['days'] if d['date']=='2028-02-29'][0];self.assertTrue(leap['today']);self.assertTrue(leap['in_month'])
        for month in ('1900-01','2100-12','2028-12','2029-01'):self.assertEqual(len(self.view(month=month)['days']),42)

    def test_latest_reminder_only_closed_withdrawn_excluded_and_overdue_strict(self):
        self.event(self.one,'applied','2028-02-20');self.event(self.one,'interview','2028-02-29');self.event(self.two,'withdrawn','2028-02-25')
        data=self.view();self.assertEqual(data['month_due'],1);self.assertEqual(data['overdue'],[])
        self.event(self.one,'interview','2028-02-28');self.assertEqual(len(self.view()['overdue']),1)
        self.event(self.one,'closed','2028-02-28');self.assertEqual(self.view()['month_due'],0)

    def test_invalid_market_month_and_bounded_data_fail_without_partial_counts(self):
        for kwargs in ({'market':'unknown'},{'month':'2028-2'},{'month':'2028-13'},{'month':'2101-01'},{'month':True},{'month':False},{'month':''},{'market':[]}):
            with self.assertRaises(ValueError):self.view(**kwargs)
        with patch('workflow_insights.records',return_value=([],[])) as read:self.assertEqual(self.view()['reviews'],0);read.assert_called_once()

    def test_read_only_and_private_notes_absent(self):
        self.event(self.one,'applied','2028-02-29');before=self.store.path.read_bytes()
        data=self.view();self.assertEqual(self.store.path.read_bytes(),before)
        self.assertNotIn('Private note',json.dumps(data));self.assertNotIn('posting',json.dumps(data));self.assertNotIn('profile',json.dumps(data))

    def test_real_sql_record_cap_refuses_partial_dashboard(self):
        with closing(sqlite3.connect(self.store.path)) as db,db:
            row=list(db.execute('SELECT * FROM jobs LIMIT 1').fetchone())
            columns=[r[1] for r in db.execute('PRAGMA table_info(jobs)')];index=columns.index('id')
            rows=[]
            for n in range(10000):
                value=list(row);value[index]='bounded-review-'+str(n);value[columns.index('title')]='Bounded review '+str(n);rows.append(value)
            db.executemany('INSERT INTO jobs VALUES ('+','.join('?' for _ in row)+')',rows)
        with self.assertRaisesRegex(ValueError,'no partial chart'):self.view()

    def test_service_validates_query_and_endpoint_has_no_writes(self):
        from web_service import WebService
        service=WebService(self.store.path)
        with self.assertRaises(ValueError):service.workflow_insights({'extra':'not accepted'})
        before=self.store.path.read_bytes();self.assertEqual(service.workflow_insights({'market':'relocation'})['reviews'],1)
        self.assertEqual(before,self.store.path.read_bytes())

    def test_invalid_history_refuses_chart(self):
        self.event(self.one,'applied')
        with closing(sqlite3.connect(self.store.path)) as db,db:db.execute('UPDATE application_events SET revision=7')
        with self.assertRaises(ValueError):self.view()
