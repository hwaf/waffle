import sys
import os
import string

def _maybequote (s):
    if s == None: return ''
    return "'" + s + "'"


class Litstring:
    def __init__ (self, s):
        self.s = s
    def __repr__ (self):
        return self.s

class Reqreader:
    def __init__ (self, args={}):
        self.private = False
        self.err = False
        self.deps = []
        self.private_deps = []
        self.install_jo = []
        self.install_python = []
        self.install_data = []
        self.install_share = []
        self.install_xml = [] 
        self.install_files = []
        self.libs = []
        self.bins = []
        self.extra_libs = []
        self.dicts = []
        self.scripts = []
        self.unittests = []
        self.root_headers = []
        self.packbase = None
        self.component = False
        self.detcommon_lib = False
        self.linked = False
        self.tpcnv = False
        self.macros = {}
        self.poolcnv_files = []
        self.sercnv_files = []
        self.cpppaths = []
        self.public_cpppaths = []
        self.libpaths = []
        self.no_rootmap = False
        self.do_ctest = False
        self.args = args
        self.tags = {}
        return

    
    def read_line (self, f):
        out = None
        while True:
            l = f.readline()
            if len(l) == 0: return out
            pos = l.find ('#')
            if pos >= 0:
                if l.strip()[-1] == '\\':
                    l = l[:pos] + '\\'
                else:
                    l = l[:pos]
            l = l.strip()
            if out:
                out = out + l
            else:
                out = l
            if out and out[-1] == '\\':
                out = out[:-1]
                if out: out = out + ' '
            elif out:
                return out
        return
    

    def translate (self, f, fout):
        self.fout = fout
        while True:
            l = self.read_line (f)
            if l == None: break
            if not l: continue
            ll = l.split()
            fn = getattr (self, 'do_' + ll[0], None)
            if fn:
                fn (ll)
            else:
                print >> sys.stderr, "Unknown req line", l
                self.err = 1
        self.dump ()
        self.check_macros()
        return


    def check_macros (self):
        self._refmacro (self.packbase + '_pedantic_level')
        
        ign = self.args.get('ignored_macros', '')
        if type(ign) == type(''): ign = ign.split()
        for k, v in self.macros.items():
            if not v[1] and not k in ign:
                print >> sys.stderr, 'Unreferenced macro', k, v[0]
                self.err = True
        return


    def _append_cpppath (self, path):
        if self.private:
            self.cpppaths.append (path)
        else:
            self.public_cpppaths.append (path)
        return


    def do_version (self, ll):
        return


   
    def do_pattern (self, ll):
        return


    def do_alias (self, ll):
        return


    def do_private (self, ll):
        self.private = True
        return

    def do_end_private (self, ll):
        self.private = False
        return

    def do_end_public (self, ll):
        #self.private = False
        return

    def do_public (self, ll):
        self.private = False
        return

    def do_branches (self, ll):
        return

    def do_package (self, ll):
        self.packbase = os.path.basename (ll[1])
        self.macros[self.packbase + '_root'] = [self.packbase + '_root', True]
        return

    def do_manager (self, ll):
        return

    def do_author (self, ll):
        return

    def do_include_dirs (self, ll):
        return

    def do_ignore_pattern (self, ll):
        return

    def do_set (self, ll):
        return

    def do_setup_script (self, ll):
        return

    def do_document (self, ll):
        if ll[1] == 'codewizard': return
        print 'Unhandled document:', ll
        self.err = True
        return

    def do_macro (self, ll):
        fl = self._macro_line (ll[2:])
        if ll[1] in ['cppdebugflags',
                     'DOXYGEN_IMAGE_PATH',
                     'CODECHECKINGOUTPUT']: return
        #if ll[1].endswith ('_linkopts'): return
        if ll[1].startswith ('DOXYGEN_'): return
        if ll[1] == 'poolcnv_include_extras' and ll[2] == '"../"': return
        if ll[1] == 'whichGroup': return
        if ll[1].endswith ('_TestConfiguration'): return

        self.macros.setdefault (ll[1], ['', False])[0] = fl
        return


    def do_macro_append (self, ll):
        fl = self._macro_line (ll[2:])
        if ll[1].startswith ('DOXYGEN_'): return
        if ll[1] == self.packbase + '_cppflags' or ll[1] == 'use_cppflags':
            fl = fl.replace ('-Wno-unused', '')
            fl = fl.replace ('-ftemplate-depth-99', '')
            if fl.strip() == '': return
        if ll[1].endswith ('_cppflags'):
            fl = fl.replace ('-DNDEBUG', '')
            if fl.strip() == '': return
        if ll[1] == 'ROOT_linkopts':
            return
        if ll[1] == 'SGFolder_testlinkopts':
            return
        if ll[1] == 'AtlasFastJet_linkopts' and fl.strip().startswith('-l'):
            self.extra_libs.append (fl.strip()[2:])
            return
        if ll[1] == 'cppflags':
            fl = fl.replace ('-Wno-format', '')
            fl = fl.replace ('-Wno-deprecated', '')
            if fl.strip() == '': return
        if ll[1].endswith ('Dict_dependencies'):
            if fl.strip() == self.packbase: return
        if ll[1].endswith ('_dependencies'):
            if fl.strip() == 'install_includes': return

        self.macros.setdefault (ll[1], ['', False])[0] += fl
        return


    def do_macro_prepend (self, ll):
        fl = self._macro_line (ll[2:])
        m = self.macros.setdefault (ll[1], ['', False])
        m[0] = fl + m[0]
        return


    def do_macro_remove (self, ll):
        if ll[1] == 'componentshr_linkopts' and ll[2] == '"-Wl,-s"':
            return
        print 'Unhandled macro_remove:', ll
        self.err = True
        return
    

    def do_use (self, ll):
        if self.private:
            deplist = self.private_deps
        else:
            deplist = self.deps

        if len(ll) < 3: return
        if len(ll) >= 4:
            path = ll[3]
        else:
            path = ''

        if ll[-1] == '-no_auto_imports': return

        self.macros[ll[1] + '_root'] = [ll[1] + '_root', True]

        if ll[1] == 'GaudiInterface':
            deplist.append ('GaudiKernel')
            return

        if ll[1] == 'GaudiPython':
            return

        if ll[1] == 'uuid':
            self.extra_libs.append ('uuid')
            return

        if ll[1] == 'AtlasPOOL':
            deplist.append ('lcg_FileCatalog')
            deplist.append ('lcg_CollectionBase')
            deplist.append ('lcg_PersistencySvc')
            deplist.append ('lcg_CoralKernel')
            deplist.append ('lcg_DataSvc')
            return

        if ll[1] == 'AtlasCORAL':
            deplist.append ('lcg_CoralBase')
            return

        if ll[1] == 'AtlasCLHEP':
            self.extra_libs.append ('CLHEP-GenericFunctions')
            self.extra_libs.append ('CLHEP-Geometry')
            self.extra_libs.append ('CLHEP-Evaluator')
            return

        if ll[1] == 'AtlasHepMC':
            self.extra_libs.append ('HepMC')
            self.extra_libs.append ('HepPDT')
            self.extra_libs.append ('HepPID')
            return

        if ll[1] == 'AtlasHdf5':
            self.extra_libs.append ('hdf5_cpp')
            self.extra_libs.append ('hdf5')
            return

        if ll[1] == 'AtlasPython':
            self.extra_libs.append ('python')
            return

        if ll[1] == 'AtlasFastJet':
            self.extra_libs.append ('SISConePlugin')
            self.extra_libs.append ('CDFConesPlugin')
            self.extra_libs.append ('CMSIterativeConePlugin')
            self.extra_libs.append ('fastjet')
            self.extra_libs.append ('siscone')
            return

        if ll[1] == 'DataCollection':
            deplist.append ('eformat')
            deplist.append ('ers')
            deplist.append ('EventStorage')
            return

        if ll[1] in ['AtlasPolicy', 'DetCommonPolicy', 'TestPolicy',
                     'AtlasFortranPolicy']:
            return

        if ll[1] == 'AtlasGSL':
            self.extra_libs.append ('gsl')
            return

        if ll[1] == 'RootHistCnv':
            self.extra_libs.append ('RootHistCnv')
            return

        if ll[1] == 'CTVMFT':
            self.libpaths.append ('$CTVMFT_HOME/build/libs')
            self.extra_libs.append ('CTVMFT')
            return

        if ll[1] == 'AtlasCERNLIB':
            self.libpaths.append ('$CERN_HOME/lib')
            self.extra_libs.append ('packlib')
            self.extra_libs.append ('mathlib')
            self.extra_libs.append ('kernlib')
            self.extra_libs.append ('$G77LIB')
            return

        if ll[1] == 'PartPropSvc':
            return

        if ll[1] == 'HepPDT':
            self.extra_libs.append ('HepPDT')
            self.extra_libs.append ('HepPID')
            return

        if ll[1] == 'ulxmlrpcpp':
            self._append_cpppath ('$ULXMLRPCPP_HOME/include')
            self.libpaths.append ('$ULXMLRPCPP_HOME/lib')
            self.extra_libs.append ('ulxmlrpcpp')
            return

        if ll[1] == 'Geant4':
            self._append_cpppath ('$GEANT_HOME/include')
            self.libpaths.append ('$GEANT_HOME/lib/Linux-g++')
            self.extra_libs += ['G4physicslists',
                                'G4materials',
                                'G4tracking',
                                'G4run',
                                'G4processes',
                                'G4event',
                                'G4particles',
                                'G4digits_hits',
                                'G4track',
                                'G4geometry',
                                'G4graphics_reps',
                                'G4intercoms',
                                'G4global']
            return
            

        if path in ['External', 'LCG_Interfaces']: return
        if path == '-no_auto_imports':
            path = ''
        pack = os.path.join (path, ll[1])
        deplist.append (pack)
        return

    def do_library (self, ll):
        if len(ll) == 2 and ll[1] == self.packbase:
            return
        if len(ll) < 3:
            print >> sys.stderr, 'Unhandled line:', ll
            self.err = True
            return
        args = self._parse_filelist (ll[2:])
        aa = [a
              for a in args if a not in ['*.cxx',
                                         '../src/*.cxx',
                                         'components/*.cxx',
                                         '../src/components/*.cxx',
                                         ]]
        if not aa: args = []
        d = {}
        args2 = []
        for a in args:
            if a.startswith ('-suffix='):
                d['objextra'] = a[8:]
            elif a == '-no_share':
                d['static'] = True
            else:
                args2.append (a)
        if args2:
            d['srcs'] = args2
        if ll[1] != self.packbase:
            d['libname'] = ll[1]
        if self.tpcnv:
            ex = d.get('except_srcs', '')
            ex = ex + ' ' + self.packbase + '.cxx'
            d['except_srcs'] = ex
        if (self.args.get ('no_components', False) and
            not d.has_key('no_components')):
            d['no_components'] = True
        self.libs.append (d)
        return


    def do_application (self, ll):
        d = {'name' : ll[1],
             'srcs' : self._parse_filelist(ll[2:])}
        self.bins.append (d)
        return


    def dopat_install_xmls (self, ll):
        aa  = self.split_args (ll)
        d = {}
        if aa.has_key ('extras'):
            d['namelist'] = \
                          self._parse_filelist (string.split (aa.get('extras')))
            del aa['extras']
        if len(aa) != 0:
            print 'Unhandled install_xmls [%s]' % self.packbase
            print ll
        self.install_xml.append (d)
        return


    def dopat_generic_declare_for_link (self, ll):
        aa = self.split_args (ll)
        if aa.has_key ('kind'):
            if aa['kind'] != 'data':
                print 'Unhandled line:', ll
                self.err = True
            del aa['kind']
        d = {}
        if aa.has_key ('prefix'):
            d['destdir'] = Litstring ("e.Dir('$BUILDDIR/%s')" % aa['prefix'])
            del aa['prefix']
        else:
            d['destdir'] = "e.Dir('$SHAREDIR')"
        files = aa['files']
        del aa['files']
        if aa:
            print 'Unhandled line:', ll
        files = self._parse_filelist (files)
        d['namelist'] = []
        for f in files:
            if f.startswith ('../'): f = f[3:]
            d['namelist'].append (f)
        d['defdir'] = 'share'
        self.install_files.append (d)
        return
    

    def _parse_filelist (self, ll):
        args = ll
        if type(args) != type(''):
            args = string.join (args)
        args = args.replace ('"', '')
        args = args.replace ("'", '')
        args = args.split()
        out = []
        dir = None
        for a in args:
            if a.startswith ('-s='):
                dir = a[3:]
                dir = self._expand_macros (dir)
                epos = dir.find ('_root/')
                if epos > 0:
                    dir = dir[epos+6:]
                
            else:
                if dir:
                    a = os.path.join (dir, a)
                out.append (a)
        return out


    def _find_macro (self, mname):
        exp = self.macros.get (mname)
        if exp == None:
            return None
        exp[1] = True
        return exp[0]
        
    def _expand_macros1 (self, ss, beg, end):
        ipos = ss.find (beg)
        while ipos >= 0:
            epos = ss.find (end, ipos)
            if epos > ipos:
                mname = ss[ipos+len(beg):epos]
                exp = self.macros.get (mname, ['', True])
                exp[1] = True
                ss = ss[:ipos] + exp[0] + ss[epos+len(end):]
            ipos = ss.find (beg, ipos+len(beg))
        return ss
    def _expand_macros (self, ss):
        ss = self._expand_macros1 (ss, '$(', ')')
        ss = self._expand_macros1 (ss, '${', '}')
        return ss


    def _refmacro (self, m, v=[]):
        if type(v) != type([]):
            v = [v]
        mval = self.macros.get (m)
        if mval:
            if v and not mval[0] in v: return
            mval[1] = True
        else:
            self.macros[m] = ['', True]
        return


    def _macro_line1 (self, ll):
        args = ll
        if type(args) != type(''):
            args = string.join (['_default'] + args)
        args = string.strip (args)
        out = []
        while args:
            pos = args.find (' ')
            if pos < 0: break
            tag = args[:pos]
            args = string.strip (args[pos:])
            if args[0] == '"' or args[0] == "'":
                pos = args.find (args[0], 1)
                if pos < 0: break
                val = args[1:pos]
                args = string.strip (args[pos+1:])
            else:
                pos = args.find (' ')
                if pos < 0:
                    val = args
                    args = ''
                else:
                    val = args[:pos]
                    args = string.strip (args[pos:])
            out.append ((tag, val))
        return out


    def _macro_line (self, ll):
        out = self._macro_line1 (ll)
        for (t, v) in out[1:]:
            if self.tags.has_key (t):
                return v
        return out[0][1]


    def do_apply_pattern (self, ll):
        if len(ll) < 2: return
        fn = getattr (self, 'dopat_' + ll[1], None)
        if fn:
            fn (ll)
        else:
            print >> sys.stderr, 'Unhandled pattern:', ll[1]
            self.err = True
        return


    def do_include_path (self, ll):
        if len(ll) == 2 and ll[1] == 'none': return
        print >> sys.stderr, 'Unhandled line', ll
        self.err = True
        return


    def do_apply_tag (self, ll):
        tag = self._expand_macros (ll[1])
        if tag in ['ROOTSTLDictLibs',
                   'ROOTTableLibs',
                   ]: return
        if tag == 'NEEDS_CORAL_BASE':
            self.extra_libs.append ('lcg_CoralBase')
            self.extra_libs.append ('lcg_CoralKernel')
            return
        if tag == 'ROOTMathLibs' or ll[1] == 'rootMathLibs':
            self.extra_libs.append ('Minuit')
            self.extra_libs.append ('Minuit2')
            return
        if tag == 'ROOTBasicLibs':
            self.extra_libs.append ('Physics')
            return
        if tag == 'ROOTPhysicsLibs':
            self.extra_libs.append ('Physics')
            return
        if tag == 'ROOTRooFitLibs':
            self.extra_libs.append ('RooFit')
            return
        if tag == 'ROOTGraphicsLibs':
            #self.extra_libs.append ('Graf')
            #self.extra_libs.append ('Graf3d')
            self.extra_libs.append ('Gpad')
            #self.extra_libs.append ('Html')
            #self.extra_libs.append ('Postscript')
            #self.extra_libs.append ('Gui')
            #self.extra_libs.append ('GX11TTF')
            #self.extra_libs.append ('GX11')
            return
        if tag == 'NEEDS_COOL_FACTORY':
            self.extra_libs.append ('lcg_CoolKernel')
            self.extra_libs.append ('lcg_CoolApplication')
            return
        if tag == 'NEEDS_CORAL_RELATIONAL_ACCESS':
            return
        if tag == 'no_rootmap':
            for d in self.dicts:
                d['rootmap'] = False
            self.no_rootmap = True
            return
        if tag == '_noAllowUndefined': return
        if tag == 'notAsNeeded': return
        print 'Unhandled line:', ll
        print 'Tag:', tag
        self.err = True
        return


    def _poolcnvns (self, f, ns, mult):
        fbase = os.path.splitext (os.path.split (f)[-1])[0]
        ismult = (fbase in mult.split())
        for n in ns.split():
            if n.endswith ('::' + fbase):
                ismult = ismult or (n in mult.split())
                if ismult: n = '*' + n
                return (f, n)
        if ismult:
            return (f, '*' + fbase)
        return f
    def dopat_poolcnv (self, ll):
        self.deps.append ('Database/AthenaPOOL/AthenaPoolCnvSvc')
        aa = self.split_args (ll)
        if aa == None:
            return
        ns = ''
        if aa.has_key ('typesWithNamespace'):
            ns = self._expand_macros (aa['typesWithNamespace'])
            del aa['typesWithNamespace']
        mult = ''
        if aa.has_key ('multChanTypes'):
            mult = aa['multChanTypes']
            del aa['multChanTypes']
        if len(aa) != 1 or not aa.has_key('files'):
            print 'Unhandled poolcnv pattern', ll
            self.err = True
            return
        ff = aa['files']

        ff = self._expand_macros (ff)

        fl = self._parse_filelist (ff)
        fl = [self._poolcnvns(f, ns, mult) for f in fl]
        self.poolcnv_files += fl

        self._refmacro (self.packbase + 'PoolCnvGen_dependencies')
        self._refmacro (self.packbase + 'PoolCnv_dependencies')
        self._refmacro (self.packbase + 'PoolCnv_shlibflags',
                        ['$(%s_linkopts)' % self.packbase,
                         '$(%s_dict_linkopts)' % self.packbase])
        self._refmacro (self.packbase + '_poolIoHdlrTypes')
        return


    def dopat_sercnv (self, ll):
        self.deps.append ('Trigger/TrigDataAccess/TrigSerializeCnvSvc')
        aa = self.split_args (ll)
        if aa == None:
            return
        ns = ''
        if aa.has_key ('typesWithNamespace'):
            ns = self._expand_macros (aa['typesWithNamespace'])
            del aa['typesWithNamespace']
        if len(aa) != 1 or not aa.has_key('files'):
            print 'Unhandled sercnv pattern', ll
            self.err = True
            return
        ff = aa['files']

        ff = self._expand_macros (ff)

        fl = self._parse_filelist (ff)
        fl = [self._poolcnvns(f, ns, '') for f in fl]
        self.sercnv_files += fl

        return

    
    def dopat_dual_use_library (self, ll):
        aa = self.split_args (ll)
        if aa == None:
            return
        if len(aa) != 1 or not aa.has_key('files'):
            print 'Unhandled dual_use_library pattern', ll
            self.err = True
            return
        args = self._parse_filelist (aa['files'])
        try:
            args.remove('*.icc')
        except ValueError:
            pass
        try:
            args.remove('*')
        except ValueError:
            pass
        aa = [a
              for a in args if a not in ['*.cxx',
                                         '../src/*.cxx',
                                         'components/*.cxx',
                                         '../src/components/*.cxx',
                                         ]]
        if not aa: args = []
        d = {'dual_use': True}
        if args:
            d['srcs'] = args
        self.libs.append (d)
        return


    def dopat_declare_joboptions (self, ll):
        aa = self.split_args (ll)
        if aa == None:
            return
        ff = aa.get('files')
        if ff.strip() == '*.py':
            ff = None
        if aa.get('files') == None or len(aa) != 1:
            print 'Unhandled declare_joboptions pattern', ll
            self.err = True
            return
        if ff:
            ff = string.join (self._parse_filelist (string.split (ff)))
        self.install_jo.append (ff)
        return


    def dopat_declare_python_modules (self, ll):
        aa = self.split_args (ll)
        if aa == None:
            return
        ff = aa.get('files')
        if ff.strip() == '*.py':
            ff = None
        if aa.get('files') == None or len(aa) != 1:
            print 'Unhandled declare_python pattern', ll
            self.err = True
            return
        if ff:
            ff = string.join (self._parse_filelist (string.split (ff)))
        self.install_python.append (ff)
        return


    def dopat_declare_jobtransforms (self, ll):
        aa = self.split_args (ll)
        if aa == None:
            return
        ff = aa.get('trfs')
        if ff:
            del aa['trfs']
            if ff[0] == "'" and ff[-1] == "'": ff = ff[1:-1]
            ff = string.join (['scripts/'+f for f in self._parse_filelist (string.split (ff))])
            self.install_python.append (ff)
        ff = aa.get('jo')
        if ff:
            del aa['jo']
            if ff[0] == "'" and ff[-1] == "'": ff = ff[1:-1]
            ff = string.join (self._parse_filelist (string.split (ff)))
            self.install_jo.append (ff)
        if aa:
            print 'Unhandled declare_jobtransforms pattern', ll
            self.err = True
        return
            


    def dopat_declare_xmls (self, ll):
        return self.dopat_install_xmls (ll)


    def dopat_static_use (self, ll):
        return

    def dopat_static_athena_app (self, ll):
        return


    def dopat_ctest (self, ll):
        if len(ll) > 2:
            print 'Unhandled ctest pattern:', ll
            self.err = True
            return
        self.do_ctest = True
        return


    def dopat_install_python_init (self, ll):
        if ll[2:]:
            print 'Unhandled install_python_init pattern', ll
            self.err = True
            return
        return self.dopat_declare_python_modules ([None, None, 'files=*.py'])


    def dopat_declare_runtime (self, ll):
        aa = self.split_args (ll)
        if not aa: return
        fl = []
        if aa.has_key('files'):
            fl += self._parse_filelist (string.split (aa.get('files')))
            del aa['files']
        if aa.has_key('extras'):
            fl += self._parse_filelist (string.split (aa.get('extras')))
            del aa['extras']
        if len(aa) != 0:
            print 'Unhandled declare_runtime pattern', ll
            self.err = True
            return
        self.install_share.append (string.join (fl))
        return


    def do_declare_runtime_extras (self, ll):
        return self.dopat_declare_runtime_extras([None] + ll)
    def dopat_declare_runtime_extras (self, ll):
        aa = self.split_args (ll)
        if not aa.has_key('extras') or len(aa) != 1:
            print 'Unhandled declare_runtime pattern', ll
            self.err = True
            return
        files = aa.get('extras')
        fl = self._parse_filelist (string.split (files))
        self.install_share.append (string.join (fl))
        return


    def dopat_component_library (self, ll):
        self.component = True
        #self.libs[-1]['component'] = True
        return


    def dopat_linked_library (self, ll):
        self.linked = True
        return


    def dopat_installed_library (self, ll):
        return


    def dopat_installed_linkopts (self, ll):
        return


    def dopat_no_include_path (self, ll):
        return


    def dopat_get_files (self, ll):
        # TODO!
        return


    def dopat_default_installed_library (self, ll):
        self.libs.append ({'srcs' : '*.cxx'})
        return


    def dopat_declare_scripts (self, ll):
        aa = self.split_args (ll)
        files = aa.get('files')
        fl = self._parse_filelist (string.split (files))
        self.scripts.append (string.join (fl))
        return


    def dopat_do_genconf (self, ll):
        return


    def dopat_tpcnv_library (self, ll):
        self.tpcnv = True
        self.libs.append ({'libname' : self.packbase + 'Load',
                           'srcs' : self.packbase + '.cxx',
                           'libs' : self.packbase,
                           'rootmap' : True})
        dd = [l for l in self.libs
              if not l.has_key('libname') or l['libname'] == self.packbase]
        if len(dd) > 0:
            d = dd[0]
            ex = d.get('except_srcs', '')
            ex = ex + ' ' + self.packbase + '.cxx'
            d['except_srcs'] = ex
        return


    def dopat_lcgdict (self, ll):
        d = {}
        aa = self.split_args (ll)
        selfile = aa.get ('selectionfile')
        if selfile != 'selection.xml':
            if not selfile.endswith ('.xml'):
                print 'Unhandled lcgdict pattern1', ll
                self.err = True
                return
            d['selfile'] = selfile
        del aa['selectionfile']
        dictname = self.packbase
        header = aa.get ('headerfiles')
        header = header.replace ('\\', '')
        header = header.replace ('-s=${%s_root}/%s ' % (self.packbase,self.packbase),
                                 '../%s/' % self.packbase)
        if header != '../%s/%sDict.h' % (self.packbase, self.packbase):
            #pos = header.rfind ('Dict')
            #if pos < 0:
            #    print 'Unhandled lcgdict pattern3', ll
            #    self.err = True
            #    return
            if not header.endswith ('.h'):
                print 'Unhandled lcgdict pattern3a', ll
                self.err = True
                return
            if header.startswith ('../'):
                header = '$PACKAGE' + header [2:]
            pat = '-s=$(' + self.packbase + '_root)/' + self.packbase
            if header.startswith (pat):
                header = header.split()[1]
            d['dictfile']  = header
        del aa['headerfiles']
        d['dictname'] = aa.get('dict')
        if not d['dictname'].endswith ('Dict'):
            d['dictname'] += 'Dict'
        del aa['dict']
        if aa.get('dataLinks'):
            dl = aa['dataLinks']
            del aa['dataLinks']
            d['dataLinks'] = string.split (self._expand_macros (dl))
        if aa.get('elementLinks'):
            dl = aa['elementLinks']
            del aa['elementLinks']
            d['elementLinks'] = string.split (self._expand_macros (dl))
        if aa.get('elementLinkVectors'):
            dl = aa['elementLinkVectors']
            del aa['elementLinkVectors']
            d['elementLinkVectors'] = string.split (self._expand_macros (dl))
        if aa.get('navigables'):
            dl = aa['navigables']
            del aa['navigables']
            d['navigables'] = string.split (self._expand_macros (dl))
        if aa:
            print 'Unhandled lcgdict pattern4', ll
            self.err = True
            return
        if self.no_rootmap:
            d['rootmap'] = False
        self.dicts.append (d)
        return


    def dopat_declare_non_standard_include (self, ll):
        aa = self.split_args (ll)
        if len(aa) == 1 and aa.get('name') == 'doc':
            return
        print 'Unhandled declare_non_standard_include', ll
        self.err= True
        return


    def dopat_UnitTest_run (self, ll):
        aa = self.split_args (ll)
        name = aa.get ('unit_test')
        if not name:
            print 'Unhandled UnitTest_run', ll
            self.err = True
            return
        del aa['unit_test']
        d = {'tests' : [name]}
        extrapat = aa.get('extrapatterns')
        if extrapat:
            d['extrapatterns'] = self._expand_macros (extrapat)
            del aa['extrapatterns']
        if len(aa) > 0:
            print 'Unhandled UnitTest_run', ll
            self.err = True
            return
        self.unittests.append (d)
        return


    def dopat_detcommon_ignores (self, ll):
        return


    def dopat_detcommon_header_installer (self, ll):
        return


    def dopat_detcommon_shared_library (self, ll):
        # Need to build dict???
        self.libs.append ({'cliddb' : False})
        return


    def dopat_trigconf_application (self, ll):
        aa = self.split_args (ll)
        name = aa['name']
        del aa['name']
        if aa:
            print 'Unhandled trigconf_application', ll
            self.err = True
        d = {'name' : 'TrigConf' + name,
             'srcs' : 'src/test/' + name + '.cxx',
             'suffix' : ''}
        self.bins.append (d)
        return


    def dopat_detcommon_link_files (self, ll):
        aa = self.split_args(ll)
        if not aa: return
        if aa.has_key('kind'):
            del aa['kind']
        if aa.has_key('name'):
            del aa['name']
        if not aa.has_key('files'):
            print 'Missing file list', ll
            self.err = True
            return
        if not aa.has_key('prefix'):
            print 'Missing prefix', ll
            self.err = True
            return
        if len(aa) != 2:
            print 'Bad detcommon_link_files', ll
            self.err = True
            return
        files = self._parse_filelist (string.split (aa.get('files')))
        d = {}
        d['destdir'] = Litstring ("e.Dir('$BUILDNAME/%s')" % aa['prefix'])
        d['namelist'] = []
        for f in files:
            if f.startswith ('../'): f = f[3:]
            d['namelist'].append (f)
        d['defdir'] = 'share'
        self.install_files.append (d)
        return


    def dopat_detcommon_shared_library_settings (self, ll):
        self.detcommon_lib = True
        return


    def dopat_install_runtime (self, ll):
        if len(ll) <= 2: return
        print 'Bad install_runtime', ll
        self.err = True
        return


    def dopat_CppUnit (self, ll):
        aa = self.split_args (ll)
        if aa.has_key ('imports'):
            self._expand_macros (aa['imports'])
        # xxx TODO!!!
        return


    def dopat_have_root_headers (self, ll):
        aa = self.split_args (ll)
        headers = aa.get ('root_headers')
        if not headers:
            print 'Unhandled have_root_headers 1', ll
            self.err = True
            return
        linkdef = None
        headers = string.split (headers)
        for i in range(len(headers)):
            if headers[i].find ('LinkDef.h') >= 0:
                linkdef = headers[i]
                del headers[i]
                break
        if not linkdef:
            print 'Unhandled have_root_headers 2', ll
            self.err = True
            return
        del aa['root_headers']

        lib = aa.get ('headers_lib')
        if not lib or (lib != self.packbase and lib != self.packbase+'Lib'):
            print 'Unhandled have_root_headers 3', ll
            self.err = True
            return
        del aa['headers_lib']

        extra_includes = aa.get ('extra_includes')
        if extra_includes:
            del aa['extra_includes']

        self.root_headers.append ((headers, linkdef, lib))
        return


    def split_args (self, ll):
        beg = None
        out = {}
        args = string.join (ll[2:])
        lastkey = None
        while True:
            args = args.strip()
            if len(args) == 0: break
            pos = args.find ('=')
            if pos < 0:
                if lastkey:
                    aa = args.split()
                    if len(aa) > 0:
                        val = aa[0]
                        args = string.join (aa[1:])
                        out[lastkey] = out[lastkey] + ' ' + val
                        continue
                print >> sys.stderr, 'Bad options1', ll
                self.err = True
                return None
            key = args[:pos].strip()
            args = args[pos+1:].strip()
            if args[0] == '"' or args[0] == "'":
                pos = args.find (args[0], 1)
                if pos < 0:
                    # No matching close quote.
                    # CMT accepts this without error.  Bleh.
                    val = args[1:]
                    args = ''
                val = args[1:pos]
                args = args[pos+1:]
            else:
                pos = args.find (' ')
                if pos < 0:
                    val = args
                    args = ''
                else:
                    val = args[:pos]
                    args = args[pos+1:]
            out[key] = val.strip()
            lastkey = key
        return out


    def dump (self):
        def _genconf_macros (n):
            v = self._find_macro ('genconfig_configurable' + n)
            if v:
                print >> self.fout, "e['GENCONF_%s'] = '%s'" % (n.upper(), v)
        _genconf_macros ('ModuleName')
        _genconf_macros ('DefaultName')
        _genconf_macros ('Algorithm')
        _genconf_macros ('AlgTool')
        _genconf_macros ('Auditor')
        _genconf_macros ('Service')

        for p in self.cpppaths:
            print >> self.fout, "e.Append(CPPPATH = '%s')"%p
        for p in self.public_cpppaths:
            print >> self.fout, "e.Append(PUBLIC_CPPFLAGS = ' -I%s')"%p
        for p in self.libpaths:
            print >> self.fout, "e.Append(LIBPATH = '%s')"%p
        for p in self.deps:
            print >> self.fout, "add_deps ('" + p + "')"
        for p in self.private_deps:
            print >> self.fout, "add_private_deps ('" + p + "')"
        for p in self.install_jo:
            print >> self.fout, "install_jo (" + _maybequote(p) + ")"
        for p in self.install_python:
            print >> self.fout, "install_python (" + _maybequote(p) + ")"
        for p in self.install_data:
            print >> self.fout, "install_data (" + _maybequote(p) + ")"
        for p in self.install_share:
            print >> self.fout, "install_share (" + _maybequote(p) + ")"
        for p in self.install_xml:
            self.print_call ('install_xml', p)
        for p in self.install_files:
            self.print_call ('install_files', p)
        extra_srcs = {}
        for (headers, linkdef, lib) in self.root_headers:
            self._refmacro (lib + '_dependencies')
            if lib.endswith ('Lib'): lib = lib[:-3]
            print >> self.fout, lib + '_cint=',
            self.print_call ('build_rootcint',
                             {'headers': headers,
                              'linkdef_in': linkdef})
            extra_srcs[lib] = Litstring (lib + '_cint')
        for d in self.libs:
            if self.component and not d.has_key ('libname'):
                d['component'] = True
            if self.extra_libs:
                d['extra_libs'] = d.get('extra_libs', []) + self.extra_libs
            if (self.detcommon_lib or self.linked) and not d.has_key ('cliddb'):
                d['cliddb'] = False
            libname = d.get ('libname', self.packbase)
            ln = libname
            if ln.endswith ('Lib'): ln = ln[:-3]
            if extra_srcs.has_key(ln):
                d.setdefault ('extra_srcs', []).append (extra_srcs[ln])
            linkopts1 = self._find_macro (libname + '_linkopts') or ''
            linkopts2 = self._find_macro (libname + 'Lib_shlibflags') or ''
            linkopts3 = self._find_macro (libname + '_shlibflags') or ''
            linkopts4 = self._find_macro (libname + '_use_linkopts') or ''
            linkopts = linkopts1 + linkopts2 + linkopts3 + linkopts4
            if linkopts:
                for o in string.split (linkopts):
                    if o.startswith ('-l'):
                        d.setdefault('extra_libs', []).append (o[2:])
                    else:
                        print 'Unrecognized linkopt for', libname, ':', o

            d['parse_flags'] = \
                            self._find_macro ('lib_' + libname + '_pp_cppflags')
                    
            self.print_call ('build_lib', d)
        for d in self.dicts:
            m = d['dictname'] + '_dependencies'
            extra = self._find_macro(m)
            if extra:
                d['extra_libs'] = d.get('extra_libs','') + ' ' + extra
            m = d['dictname'] + '_shlibflags'
            extra = self._find_macro(m)
            if extra:
                for e in extra.split():
                    e = e.replace ('"', '')
                    e = e.strip()
                    if e.startswith ('-l'):
                        d['extra_libs'] = d.get('extra_libs','') + ' ' + e[2:]
                    else:
                        print 'Unhandled shlibflags', m, extra
                        self.errflag = True
            self.print_call ('build_dict', d)
        if self.poolcnv_files:
            self.print_call ('build_poolcnv',
                             {'names' : self.poolcnv_files})
        if self.sercnv_files:
            self.print_call ('build_sercnv',
                             {'names' : self.sercnv_files})
        for d in self.bins:
            if self.extra_libs:
                d['libs'] = d.get('libs', []) + self.extra_libs
            self._refmacro (d['name'] + '_dependencies')
            # cf typo in OverlayValidation
            self._refmacro (d['name'] + '_dependenciies')
            self.print_call ('build_bin', d)
        if self.scripts:
            print >> self.fout,\
                  "install_scripts ('" + string.join (self.scripts) + "')"
        for d in self.unittests:
            self.print_call ('build_tests', d)
        if self.do_ctest:
            self.print_call ('build_ctests', {})
        return


    def print_call (self, fn, d):
        lead = '%s (' % fn
        indent = ''
        print >> self.fout, lead,
        for (k, v) in d.items():
            print >> self.fout, ('%s%s = %s,' % (indent, k, repr(v))),
            indent = '\n' + ' ' * len (lead)
        print >> self.fout, ')'
        return
        
        


if __name__ == "__main__":
    import sys
    r = Reqreader()
    r.translate (open(sys.argv[1]), sys.stdout)
