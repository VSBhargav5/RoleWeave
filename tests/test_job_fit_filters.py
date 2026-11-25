import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from job_fit_filters import DEFAULT, classify, decision, filter_result, preferences, discovery_view
from job_search import parse_search
from web_service import WebService
from workspace_bundle import export_bundle, restore_bundle, recovered_database


def observed(identifier='india',location='India',posting='3-5 years of data engineering experience required.'):
    return {'public_slug':identifier,'title':'Data Engineer','company':'Synthetic employer','description':posting,
            'url':'https://example.invalid/'+identifier,'location':location,'work_mode':'remote'}


def info(posting,location='India',mode='remote',title='Data Engineer'):
    return classify({'posting':posting,'location':location,'work_mode':mode,'title':title})


class FitFilterTests(unittest.TestCase):
    def test_version_two_title_matching_separates_role_search_from_keywords(self):
        from job_fit_filters import role_matches
        for title in ('Senior Data Engineer','Data Integration Engineer - Bangalore','Analytics Engineer','ETL Developer'):
            self.assertTrue(role_matches(title,'data engineer'),title)
        for title in ('Mechanical Engineer','Chemical Engineer','Data Analyst'):
            self.assertFalse(role_matches(title,'data engineer'),title)
        rows=[{'id':str(i),'title':title,'posting':'Data engineer collaboration. *Experience:* 5 Years.','location':'Bengaluru','work_mode':'onsite'}
              for i,title in enumerate(('Data Engineer','Chemical Engineer','Mechanical Engineer'))]
        result={'jobs':rows,'excluded':[]}
        selection=DEFAULT|{'version':2,'role_query':'data engineer','experience':'3-5'}
        filtered=filter_result(result,selection)
        self.assertEqual([j['title'] for j in filtered['jobs']],['Data Engineer'])
        self.assertEqual(len(filter_result(result,selection|{'role_query':''})['jobs']),3)
        self.assertEqual(len(filter_result(result,DEFAULT)['jobs']),3,'v1 replay must keep its original classifier')
        self.assertIsNone(classify(rows[0])['minimum'])
        self.assertEqual(classify(rows[0],2)['minimum'],5)
        with self.assertRaises(ValueError):preferences(selection|{'role_query':123})

    def test_advertised_year_bands_use_explicit_minimum_not_seniority_or_salary(self):
        for posting,minimum in [('0-2 years of experience.',0),('3+ years of experience required.',3),('Experience required: 3-5 years.',3),
                                ('Minimum 8 years of professional experience.',8),
                                ('3-5 years of data engineering experience required.',3),
                                ('No prior experience required.',0),
                                ('Senior engineer. Salary 200000. Founded in 2005.',None)]:
            with self.subTest(posting=posting):self.assertEqual(info(posting)['minimum'],minimum)
        self.assertEqual(info('3+ years of experience required.\nPreferred skills\n10 years of experience.')['minimum'],3)
        self.assertEqual(info('3+ years of experience required. 10 years of experience preferred.')['minimum'],3)
        self.assertEqual(info('Our company has 20 years of experience. You need 3 years of experience.')['minimum'],3)
        self.assertIsNone(info("Bachelor degree and 6 years of experience or Masters and 3 years of experience.")['minimum'])

    def test_canada_residence_restriction_overrides_remote_and_india_metadata(self):
        posting='This is a remote position open to candidates residing in Canada. Relocation assistance will not be provided for this role.'
        item=info(posting)
        self.assertEqual(item['countries'],['CA'])
        self.assertEqual(decision(item,DEFAULT)[0],'excluded')
        self.assertEqual(decision(item,DEFAULT|{'residence':'CA'})[0],'match')
        self.assertEqual(decision(info('Python required.','Remote - Canada'),DEFAULT)[0],'excluded')
        self.assertEqual(decision(info('Python required.','Remote',title='Data Engineer - Remote - Canada'),DEFAULT)[0],'excluded')

    def test_office_mentions_are_not_residence_requirements_and_unknown_is_separate(self):
        self.assertEqual(decision(info('Our team has offices in Canada and India.','Remote'),DEFAULT)[0],'excluded')
        self.assertEqual(decision(info('Our team has offices in Canada and India.','Remote'),DEFAULT|{'include_unknown':True})[0],'review')
        self.assertEqual(decision(info('Remote worldwide.','Canada'),DEFAULT)[0],'match')
        self.assertEqual(decision(info('Work from anywhere. Applicants must reside in Canada.','Worldwide'),DEFAULT)[0],'excluded')
        self.assertEqual(decision(info('Must reside in Hungary.','India'),DEFAULT)[0],'excluded')
        self.assertEqual(decision(info('No remote work.','India','onsite'),DEFAULT,True)[0],'excluded')
        self.assertEqual(decision(info('Remote work two days per week.','India','hybrid'),DEFAULT,True)[0],'excluded')
        self.assertFalse(info('Python required.','Bengaluru','Not marked remote by provider')['remote'])

    def test_unknown_experience_is_not_invented_and_bands_exclude_higher_requirements(self):
        selected=DEFAULT|{'experience':'3-5'}
        self.assertEqual(decision(info('8+ years of experience required.'),selected)[0],'excluded')
        self.assertEqual(decision(info('3+ years of experience required.'),selected)[0],'match')
        self.assertEqual(decision(info('Senior Python engineer.'),selected)[0],'excluded')
        self.assertEqual(decision(info('Senior Python engineer.'),selected|{'include_unknown':True})[0],'review')
        for value in (DEFAULT|{'version':True},DEFAULT|{'experience':'senior'},DEFAULT|{'residence':'Canada'},DEFAULT|{'include_unknown':1}):
            with self.assertRaises(ValueError):preferences(value)


class SearchFitIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.service=WebService(self.root/'jobs.db')
        rows=[observed(),observed('senior',posting='8+ years of experience required.'),
              observed('canada','Remote - Canada'),observed('world','Worldwide'),
              observed('unclear','Remote'),observed('no-years',posting='Python required.')]
        self.raw=json.dumps({'data':rows,'meta':{'offset':0,'limit':20,'total':6}}).encode()
        self.page=parse_search(self.raw);self.service.searcher.search=Mock(return_value=self.page)
        self.service.searcher.snapshots[self.page['source_sha256']]=self.raw
        self.selection=DEFAULT|{'experience':'3-5'}

    def test_page_filter_preserves_raw_cache_source_and_pagination(self):
        before=copy.deepcopy(self.page)
        result=self.service.search({'query':'data engineer','country':'IN','remote':True,'preferences':self.selection})
        self.assertEqual([r['id'] for r in result['jobs']],['india','world'])
        self.service.searcher.search.assert_called_once_with('data engineer','','IN',True,0)
        self.assertEqual(result['page'],before['page']);self.assertEqual(result['total'],6)
        self.assertEqual(len(result['excluded']),4);self.assertEqual(self.page,before)
        result=self.service.search({'query':'data engineer','remote':True,'preferences':self.selection|{'include_unknown':True}})
        self.assertEqual([r['id'] for r in result['jobs']],['india','world','unclear','no-years'])
        self.assertEqual(result['fit']['rows']['unclear']['state'],'review')
        self.assertEqual(len(self.service.search({'query':'data engineer'})['jobs']),6,'Older API clients keep the old unfiltered contract')
        # JSearch local preferences stay out of the provider request, and can override
        # a misleading provider country label when the description states residency.
        from test_jsearch import filters, response, raw_job
        self.addCleanup(self.service.jsearch.shutdown)
        preview=self.service.jsearch_preview(filters(remote=True)|{'preferences':DEFAULT})
        raw=response([raw_job(job_is_remote=True,job_description='Remote position open to candidates residing in Canada.')])
        with patch('jsearch_session.request',return_value=raw) as provider:
            self.service.jsearch.send({'id':preview['id'],'sha256':preview['sha256'],'key':'synthetic-filter-key','confirmed':True})
            self.service.jsearch.entries[preview['id']]['thread'].join(3)
        self.assertNotIn('preferences',provider.call_args.args[0])
        result=self.service.jsearch_status({'id':preview['id']})
        self.assertEqual(result['status'],'completed');self.assertEqual(result['result']['jobs'],[])
        self.assertEqual(len(result['result']['excluded']),1)

    def test_saved_filters_and_filtered_counts_survive_source_replay_and_recovery(self):
        self.selection=self.selection|{'version':2,'role_query':'data engineer'}
        config={'name':'Relevant data roles','query':'data engineer','location':'India','country':'IN','remote':True,
                'market':'india_remote','archived':False,'preferences':self.selection,'expected_revision':0}
        state=self.service.save_discovery_search(config);saved=state['searches'][0]
        state=self.service.run_discovery({'id':saved['id'],'expected_revision':state['revision'],'confirmed':True,'preferences':self.selection})
        self.assertEqual(len(state['candidates']),2);self.assertEqual(state['runs'][0]['excluded'],4)
        self.assertEqual(state['runs'][0]['search']['preferences'],self.selection)
        bundle=export_bundle(self.service.store,self.service.artifacts)
        result=restore_bundle(bundle,self.root/'restored')
        recovered=WebService(recovered_database(self.root/'restored',result['id']))
        self.assertEqual(recovered.discovery.read(),state)
        self.assertEqual(len(discovery_view(recovered.discovery.read())['classifications']),2)


if __name__=='__main__':unittest.main()
