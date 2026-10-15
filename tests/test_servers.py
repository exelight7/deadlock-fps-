import copy,json,tempfile,unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch
from deadlock_fps.servers import parse_catalog,ServerStore,Relay,checked_relay
from deadlock_fps.firewall import validate_plan,linux_apply,windows_apply,rule_name,CHAIN
DATA={'revision':1,'pops':{
 'dxb':{'desc':'Dubai','relays':[{'ipv4':'185.25.183.163','port_range':[27015,27060]}]},
 'fra':{'desc':'Frankfurt','relays':[{'ipv4':'155.133.226.68','port_range':[27015,27060]}]},
 'alias':{'desc':'Alias, no relay'}}}
class Servers(unittest.TestCase):
    def test_parse_limits_and_public_addresses(self):
        regions=parse_catalog(DATA);self.assertEqual([r.code for r in regions],['dxb','fra'])
        for bad in ['127.0.0.1','192.168.1.1','8.8.8.8; touch /tmp/pwn','::1']:
            with self.assertRaises(ValueError):checked_relay(bad,1,2)
        with self.assertRaises(ValueError):checked_relay('8.8.8.8',0,65536)
    def test_presets_and_only_selection(self):
        with tempfile.TemporaryDirectory() as d:
            store=ServerStore(d);regions=parse_catalog(DATA);store.save_preset('Dubai',['dxb'])
            plan,blocked=store.plan(regions,{'dxb'},'only');self.assertEqual(blocked,['fra']);self.assertEqual(plan['new'][0]['ip'],'155.133.226.68')
            store.record(blocked,plan['new']);self.assertEqual(store.state()['presets']['Dubai'],['dxb'])
            plan,blocked=store.plan(regions,{'fra'},'unblock');self.assertEqual(plan['new'],[]);self.assertEqual(blocked,[])
            with self.assertRaises(ValueError):store.plan(regions,set(),'only')
    def test_shared_allowed_relay_is_never_blocked(self):
        data=copy.deepcopy(DATA);data['pops']['fra']['relays']=data['pops']['dxb']['relays']
        with tempfile.TemporaryDirectory() as d:
            plan,blocked=ServerStore(d).plan(parse_catalog(data),{'dxb'},'only');self.assertEqual(plan['new'],[])
    def test_shared_overlapping_ports_remain_available(self):
        from deadlock_fps.servers import exclude_shared
        blocked=[Relay('8.8.8.8',100,200)];allowed=[Relay('8.8.8.8',125,175)]
        self.assertEqual(exclude_shared(blocked,allowed),[Relay('8.8.8.8',100,124),Relay('8.8.8.8',176,200)])
    def test_offline_snapshot_available(self):
        with tempfile.TemporaryDirectory() as d:
            regions,revision=ServerStore(d).load_catalog();self.assertTrue(any(r.code=='dxb' for r in regions));self.assertTrue(revision)
    def test_ping_reports_fractional_loss(self):
        from deadlock_fps.servers import ping_region
        region=parse_catalog(DATA)[0]
        completed=CompletedProcess([],0,'64 bytes time=20.0 ms\n64 bytes time=22.0 ms\n','')
        with patch('deadlock_fps.servers.os.name','posix'),patch('subprocess.run',return_value=completed):
            self.assertEqual(ping_region(region),(21.0,33))
    def test_bad_download_does_not_replace_cache(self):
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as d:
            store=ServerStore(d);store.cache.write_text(json.dumps(DATA));original=store.cache.read_bytes()
            response=MagicMock();response.__enter__.return_value=response;response.geturl.return_value='https://api.steampowered.com/ISteamApps/GetSDRConfig/v1/';response.read.return_value=b'{broken'
            with patch('urllib.request.urlopen',return_value=response):
                with self.assertRaises(ValueError):store.refresh()
            self.assertEqual(store.cache.read_bytes(),original)

class FirewallPlans(unittest.TestCase):
    def plan(self):return validate_plan({'schema':1,'old':[],'new':[{'ip':'185.25.183.163','first':27015,'last':27060}]})
    def test_rejects_injection_and_unbounded_input(self):
        for row in [{'ip':'8.8.8.8;id','first':1,'last':2},{'ip':'8.8.8.8','first':'1;id','last':2},{'ip':'8.8.8.8','first':1,'last':2,'cmd':'id'}]:
            with self.assertRaises((ValueError,TypeError)):validate_plan({'schema':1,'old':[],'new':[row]})
        with self.assertRaises(ValueError):validate_plan({'schema':1,'old':[],'new':[],'reset':'yes'})
    def test_linux_changes_only_own_chain(self):
        calls=[]
        def run(args,**kwargs):
            calls.append((args,kwargs));return CompletedProcess(args,1 if '-S' in args or '-C' in args else 0,'','')
        with patch('shutil.which',side_effect=lambda x:'/usr/sbin/'+x):linux_apply(self.plan(),run)
        restore=next(k['input'] for a,k in calls if a[0].endswith('iptables-restore'))
        self.assertIn('-F '+CHAIN,restore);self.assertIn('--dport 27015:27060',restore);self.assertNotIn('-F OUTPUT',restore)
        self.assertTrue(any(a[-4:]==['OUTPUT','1','-j',CHAIN] for a,k in calls))
    def test_linux_failure_rolls_back_owned_rules(self):
        calls=[];old=f'-N {CHAIN}\n-A {CHAIN} -d 8.8.8.8 -p udp --dport 27015:27060 -j DROP\n'
        def run(args,**kwargs):
            calls.append((args,kwargs))
            if '-S' in args:return CompletedProcess(args,0,old,'')
            if '-C' in args:return CompletedProcess(args,1,'','')
            if '-I' in args:return CompletedProcess(args,1,'','simulated insert error')
            return CompletedProcess(args,0,'','')
        with patch('shutil.which',side_effect=lambda x:'/usr/sbin/'+x):
            with self.assertRaises(RuntimeError):linux_apply(self.plan(),run)
        restore=[k['input'] for a,k in calls if 'input' in k];self.assertEqual(len(restore),2);self.assertIn('8.8.8.8',restore[-1])
    def test_linux_clear_does_not_flush_other_chains(self):
        calls=[]
        def run(args,**kwargs):
            calls.append(args);return CompletedProcess(args,1 if '-C' in args else 0,'','')
        with patch('shutil.which',side_effect=lambda x:'/usr/sbin/'+x):linux_apply(validate_plan({'schema':1,'old':[],'new':[],'reset':True}),run)
        self.assertTrue(any(a[-2:]==['-F',CHAIN] for a in calls));self.assertFalse(any(a[-1]=='-F' for a in calls))
    def test_windows_uses_specific_names_and_udp_ports(self):
        calls=[]
        def run(args,**kwargs):
            calls.append(args);return CompletedProcess(args,1 if 'show' in args else 0,'','')
        windows_apply(self.plan(),run)
        add=next(a for a in calls if 'add' in a);self.assertIn('protocol=UDP',add);self.assertIn('remoteport=27015-27060',add)
        self.assertTrue(any(a.startswith('name=DeadlockToolbox_SDR_') for a in add))
    def test_windows_failure_rolls_back_added_rules(self):
        plan=self.plan();plan['new'].append(Relay('155.133.226.68',27015,27060));calls=[];adds=0
        def run(args,**kwargs):
            nonlocal adds
            calls.append(args)
            if 'show' in args:return CompletedProcess(args,1,'','')
            if 'add' in args:
                adds+=1
                if adds==2:return CompletedProcess(args,1,'','simulated error')
            return CompletedProcess(args,0,'','')
        with self.assertRaises(RuntimeError):windows_apply(plan,run)
        self.assertTrue(any('delete' in a for a in calls))
    def test_windows_reset_is_namespace_scoped(self):
        calls=[]
        def run(args,**kwargs):calls.append(args);return CompletedProcess(args,0,'','')
        windows_apply(validate_plan({'schema':1,'old':[],'new':[],'reset':True}),run)
        self.assertIn('DeadlockToolbox_SDR_',calls[0][-1]);self.assertNotIn('advfirewall reset',' '.join(calls[0]))
        self.assertIn("-DisplayName 'DeadlockToolbox_SDR_*'",calls[0][-1])
        self.assertIn('$_.DisplayName -match',calls[0][-1])

class Interface(unittest.TestCase):
    def test_servers_are_native_and_name_is_new(self):
        from PySide6.QtWidgets import QApplication
        from deadlock_fps.ui import Window
        app=QApplication.instance() or QApplication([]);w=Window();w.guard_timer.stop()
        self.assertEqual(w.windowTitle(),'Deadlock Toolbox');w.navigate(4);self.assertEqual(w.stack.currentIndex(),4)
        self.assertGreater(w.servers.table.rowCount(),10);self.assertIn('السيرفرات',w.nav[4].text());w.close()
