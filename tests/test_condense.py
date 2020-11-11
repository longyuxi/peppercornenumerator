#!/usr/bin/env python
#
#  test_condense.py
#  EnumeratorProject
#
import unittest

from peppercornenumerator.input import read_pil
from peppercornenumerator.enumerator import Enumerator

from peppercornenumerator.objects import (clear_memory,
                                          SingletonError,
                                          PepperDomain,
                                          PepperComplex,
                                          PepperReaction,
                                          PepperMacrostate)

from peppercornenumerator.condense import (SetOfFates, 
                                           PepperCondensation,
                                           cartesian_sum,
                                           tuple_sum,
                                           cartesian_product)

SKIP = False

class SetOfFatesTest(unittest.TestCase):
    pass

@unittest.skipIf(SKIP, "skipping tests")
class UtilityTests(unittest.TestCase):
    def test_cartesian_product(self):
        A = [('a', 'a', 'b'), ('c', 'b')]
        B = [('a', 'b', 'c'), ('b', 'c')]
        assert list(cartesian_product((A, B))) == [(('a', 'a', 'b'), ('a', 'b', 'c')), 
                                             (('a', 'a', 'b'), ('b', 'c')), 
                                             (('c', 'b'), ('a', 'b', 'c')), 
                                             (('c', 'b'), ('b', 'c'))]

        A = ('x', 'y', 'z')
        B = ('1', '2', '3')
        assert list(cartesian_product((A, B))) == [('x', '1'), ('x', '2'), ('x', '3'), 
                                             ('y', '1'), ('y', '2'), ('y', '3'), 
                                             ('z', '1'), ('z', '2'), ('z', '3')]

        A = (('x',), ('1', 'x'))
        B = (('1',), ('2',), ('3',))
        C = (('x',), ('1',))
        assert list(cartesian_product((A, B, C))) == [(('x',), ('1',), ('x',)), 
                                                (('x',), ('1',), ('1',)), 
                                                (('x',), ('2',), ('x',)), 
                                                (('x',), ('2',), ('1',)), 
                                                (('x',), ('3',), ('x',)), 
                                                (('x',), ('3',), ('1',)),
                                                (('1', 'x'), ('1',), ('x',)), 
                                                (('1', 'x'), ('1',), ('1',)), 
                                                (('1', 'x'), ('2',), ('x',)), 
                                                (('1', 'x'), ('2',), ('1',)), 
                                                (('1', 'x'), ('3',), ('x',)), 
                                                (('1', 'x'), ('3',), ('1',))]

    def test_cartesian_sum(self):
        x = (('a',), ('b',)) 
        y = (('c',), ('d',)) 
        self.assertEqual(cartesian_sum([x,y]), [('a', 'c'), ('a', 'd'), 
                                                ('b', 'c'), ('b', 'd')])

        x = (('a',), ('a',)) 
        y = (('c',), ('d',)) 
        self.assertEqual(cartesian_sum([x,y]), [('a', 'c'), ('a', 'd'), 
                                                ('a', 'c'), ('a', 'd')])

        x = () 
        y = (('c',), ('d',)) 
        self.assertEqual(cartesian_sum([x,y]), [])

        x = (('c',),)
        y = (('c',), ('d',)) 
        self.assertEqual(cartesian_sum([x,y]), [('c', 'c'), ('c', 'd')])

        x = [(1,), (2, 3)] 
        y = [(4, 5, 6), (7, 8)]
        self.assertEqual(cartesian_sum([x,y]),
            [(1, 4, 5, 6), (1, 7, 8), (2, 3, 4, 5, 6), (2, 3, 7, 8)])

    def test_tuplesum(self):
        self.assertEqual(tuple_sum([(1, 2, 3), (6,), (5, 4, 7)]), (1, 2, 3, 4, 5, 6, 7))

    def todotestTarjans(self):
        pass

    def todotestGetReactionsConsuming(self):
        pass

    def todotestIsOutgoing(self):
        pass

@unittest.skipIf(SKIP, "skipping tests")
class CondenseTests(unittest.TestCase):
    # TODO: I want a test where we have the same reaction exiting an SCC multiple times.
    # does that exist?
    def tearDown(self):
        clear_memory()

    def test_condense_simple(self):
        complexes, reactions = read_pil("""
        # File generated by peppercorn-v0.5.0
        
        # Domain Specifications 
        length d1 = 15
        length t0 = 5
        
        # Resting-set Complexes 
        c1 = t0 d1 
        c2 = d1( + ) t0* 
        c4 = t0( d1( + ) ) 
        c5 = d1 
        
        # Transient Complexes 
        c3 = t0( d1 + d1( + ) ) 
        
        # Detailed Reactions 
        reaction [bind21         =      100 /M/s ] c1 + c2 -> c3
        reaction [open           =       50 /s   ] c3 -> c1 + c2
        reaction [branch-3way    =       50 /s   ] c3 -> c4 + c5
        """)

        # (rs1) c1                c4 (rs3)
        #         \              /
        #          <---> c3 ---->
        #         /              \
        # (rs2) c2                c5 (rs4)

        enum = Enumerator(complexes.values(), reactions)
        enum.enumerate() 
        enum.condense()
        for con in enum.condensed_reactions:
            assert con.rate_constant[0] == 50
        del enum

        # old interface ...
        c1 = PepperMacrostate([complexes['c1']])
        c2 = PepperMacrostate([complexes['c2']])
        c4 = PepperMacrostate([complexes['c4']])
        c5 = PepperMacrostate([complexes['c5']])
        cond_react = PepperReaction([c1, c2], [c4, c5], 'condensed')
        cond_react.rate_constant = 20, None

        enum = Enumerator(complexes.values(), reactions)
        enum.dry_run()
        enumRG = PepperCondensation(enum)
        enumRG.condense()
        for con in enumRG.condensed_reactions:
            assert con.rate_constant[0] == 20

    def test_zhang_cooperative_binding(self):
        complexes, reactions = read_pil("""
        # Figure 1 of David Yu Zhang, "Cooperative hybridization of oligonucleotides", JACS, 2012

        # File generated by peppercorn-v0.5.0

        # Domain Specifications 
        length d1 = 8
        length d2 = 18
        length d3 = 18
        length d4 = 8

        # Resting-set Complexes 
        C1 = d2( d3( + d4* ) ) d1* 
        L1 = d1( d2 + d2( d3( + d4* ) ) ) 
        L2 = d1( d2( + d2 d3( + d4* ) ) ) 
        Out = d2 d3 
        R1 = d2( d3( + d3 d4( + ) ) ) d1* 
        R2 = d2( d3 + d3( d4( + ) ) ) d1* 
        T1 = d1 d2 
        T2 = d3 d4 
        Waste = d1( d2( + d3( d4( + ) ) ) ) 

        # Transient Complexes 
        L1R1 = d1( d2 + d2( d3( + d3 d4( + ) ) ) ) 
        L1R2 = d1( d2 + d2( d3 + d3( d4( + ) ) ) ) 
        L2R1 = d1( d2( + d2 d3( + d3 d4( + ) ) ) ) 

        # Detailed Reactions 
        reaction [bind21         =      2.4e+06 /M/s ] C1 + T2 -> R1
        reaction [bind21         =      2.4e+06 /M/s ] L1 + T2 -> L1R1
        reaction [branch-3way    =      18.5185 /s   ] L1 -> L2
        reaction [branch-3way    =      18.5185 /s   ] L1R1 -> L1R2
        reaction [branch-3way    =      18.5185 /s   ] L1R1 -> L2R1
        reaction [branch-3way    =      18.5185 /s   ] L1R2 -> L1R1
        reaction [branch-3way    =      18.5185 /s   ] L1R2 -> Waste + Out
        reaction [bind21         =      2.4e+06 /M/s ] L2 + T2 -> L2R1
        reaction [branch-3way    =      18.5185 /s   ] L2 -> L1
        reaction [branch-3way    =      18.5185 /s   ] L2R1 -> L1R1
        reaction [branch-3way    =      18.5185 /s   ] L2R1 -> Waste + Out
        reaction [branch-3way    =      18.5185 /s   ] R1 -> R2
        reaction [branch-3way    =      18.5185 /s   ] R2 -> R1
        reaction [bind21         =      2.4e+06 /M/s ] T1 + C1 -> L1
        reaction [bind21         =      2.4e+06 /M/s ] T1 + R1 -> L1R1
        reaction [bind21         =      2.4e+06 /M/s ] T1 + R2 -> L1R2
        """)

        enum = Enumerator(complexes.values(), reactions)
        enum.k_fast = 0.01 
        enum.release_cutoff = 10
        enum.enumerate() # or enum.dry_run()

        enumRG = PepperCondensation(enum)
        enumRG.condense()
        
        """
        macrostate rC1 = [C1]
        macrostate rL2 = [L2, L1]
        macrostate rOut = [Out]
        macrostate rR1 = [R1, R2]
        macrostate rT1 = [T1]
        macrostate rT2 = [T2]
        macrostate rWaste = [Waste]

        reaction [condensed      =      2.4e+06 /M/s ] rT1 + rC1 -> rL2
        reaction [condensed      =      2.4e+06 /M/s ] rL2 + rT2 -> rWaste + rOut
        reaction [condensed      =      2.4e+06 /M/s ] rC1 + rT2 -> rR1
        reaction [condensed      =      2.4e+06 /M/s ] rT1 + rR1 -> rWaste + rOut
        reaction [condensed      =   0.00316623 /s   ] rL2 -> rT1 + rC1
        reaction [condensed      =   0.00316623 /s   ] rR1 -> rC1 + rT2
        """
        
        try:
            L1 = complexes['L1']
            L2 = complexes['L2']
            L = PepperMacrostate([L1, L2])
        except SingletonError as err:
            L = err.existing
        O = PepperMacrostate([complexes['Out']])
        W = PepperMacrostate([complexes['Waste']])
        T = PepperMacrostate([complexes['T2']])

        # calculated by hand...
        cr1 = PepperReaction([L, T], [W, O], 'condensed')
        assert cr1 in enumRG.condensed_reactions
        assert cr1.rate_constant == (2.4e6, '/M/s')

    def test_cooperative_binding(self):
        # cooperative binding with k-fast 25
        complexes, reactions = read_pil("""
        # File generated by peppercorn-v0.5.0
        
        # Domain Specifications 
        length a = 5
        length b = 5
        length x = 10
        length y = 10
        
        # Resting-set Complexes 
        C = x( y( + b* ) ) a* 
        CR = x( y( + y b( + ) ) ) a* 
        CRF = x( y + y( b( + ) ) ) a* 
        L = a x 
        LC = a( x + x( y( + b* ) ) ) 
        LCF = a( x( + x y( + b* ) ) ) 
        LR = a( x( + y( b( + ) ) ) ) 
        R = y b 
        T = x y 
        
        # Transient Complexes 
        LCR = a( x + x( y( + y b( + ) ) ) ) 
        LCRF1 = a( x( + x y( + y b( + ) ) ) ) 
        LCRF2 = a( x + x( y + y( b( + ) ) ) ) 
        
        # Detailed Reactions 
        reaction [bind21         =      1.5e+06 /M/s ] C + L -> LC
        reaction [bind21         =      1.5e+06 /M/s ] C + R -> CR
        reaction [open           =           20 /s   ] CR -> C + R
        reaction [branch-3way    =           30 /s   ] CR -> CRF
        reaction [branch-3way    =           30 /s   ] CRF -> CR
        reaction [bind21         =      1.5e+06 /M/s ] L + CR -> LCR
        reaction [bind21         =      1.5e+06 /M/s ] L + CRF -> LCRF2
        reaction [open           =           20 /s   ] LC -> C + L
        reaction [branch-3way    =           30 /s   ] LC -> LCF
        reaction [branch-3way    =           30 /s   ] LCF -> LC
        reaction [branch-3way    =           30 /s   ] LCR -> LCRF1
        reaction [branch-3way    =           30 /s   ] LCR -> LCRF2
        reaction [branch-3way    =           30 /s   ] LCRF1 -> LCR
        reaction [branch-3way    =           30 /s   ] LCRF1 -> T + LR
        reaction [branch-3way    =           30 /s   ] LCRF2 -> LCR
        reaction [branch-3way    =           30 /s   ] LCRF2 -> T + LR
        reaction [bind21         =      1.5e+06 /M/s ] R + LC -> LCR
        reaction [bind21         =      1.5e+06 /M/s ] R + LCF -> LCRF1
        """)
        L = complexes['L']
        C = complexes['C']
        R = complexes['R']
        T = complexes['T']
        LR = complexes['LR']
        LC = complexes['LC']
        CR = complexes['CR']
        CRF = complexes['CRF']
        LCF = complexes['LCF']
        LCR = complexes['LCR']
        LCRF1 = complexes['LCRF1']
        LCRF2 = complexes['LCRF2']

        rs1 = PepperMacrostate([L]) 
        rs2 = PepperMacrostate([C])
        rs3 = PepperMacrostate([R])
        rs4 = PepperMacrostate([T])
        rs5 = PepperMacrostate([LR])
        rs6 = PepperMacrostate([CR, CRF])
        rs7 = PepperMacrostate([LC, LCF])

        cplx_to_fate = { # maps Complex to its SetOfFates
                L  : SetOfFates([[rs1]]), 
                C  : SetOfFates([[rs2]]),
                R  : SetOfFates([[rs3]]),
                T  : SetOfFates([[rs4]]),
                LR : SetOfFates([[rs5]]),
                CR  : SetOfFates([[rs6]]),
                CRF : SetOfFates([[rs6]]),
                LC  : SetOfFates([[rs7]]),
                LCF : SetOfFates([[rs7]]),
                #NOTE: only rs4 and rs5 bec. the other unimolecular reactions are now slow!!
                LCR : SetOfFates([[rs4, rs5]]),
                LCRF1 : SetOfFates([[rs4, rs5]]),
                LCRF2 : SetOfFates([[rs4, rs5]])}

        enum = Enumerator(complexes.values(), reactions)
        enum.k_fast = 25
        enum.dry_run() # or enum.enumerate()
        enumRG = PepperCondensation(enum)
        enumRG.condense()

        cr1  = PepperReaction([rs1, rs2], [rs7], 'condensed')
        self.assertAlmostEqual(cr1.rate_constant[0], 1.5e6)
        cr2  = PepperReaction([rs2, rs3], [rs6], 'condensed')
        self.assertAlmostEqual(cr2.rate_constant[0], 1.5e6)

        # not sure how these rates were computed...
        cr1r = PepperReaction([rs7], [rs1, rs2], 'condensed')
        assert cr1r.rate_constant == (10, '/s')
        cr2r = PepperReaction([rs6], [rs2, rs3], 'condensed')
        assert cr2r.rate_constant == (10, '/s')
        cr3  = PepperReaction([rs1, rs6], [rs5, rs4], 'condensed')
        self.assertAlmostEqual(cr3.rate_constant[0], 3e6/2)
        #assert cr3.rate_constant == (3e6/2, '/M/s')
        cr4  = PepperReaction([rs3, rs7], [rs5, rs4], 'condensed')
        self.assertAlmostEqual(cr4.rate_constant[0], 3e6/2)
        #assert cr4.rate_constant == (3e6/2, '/M/s')

        self.assertEqual(sorted([rs1, rs2, rs3, rs4, rs5, rs6, rs7]),  
                         sorted(enumRG.resting_macrostates))

        self.assertDictEqual(cplx_to_fate, enumRG._complex_fates)
        self.assertEqual(sorted([cr1, cr1r, cr2, cr2r, cr3, cr4]), 
                         sorted(enumRG.condensed_reactions))

    def test_cooperative_binding_fail(self):
        complexes, reactions = read_pil("""
        # File generated by peppercorn-v0.5.0
        
        # Domain Specifications 
        length a = 5
        length b = 5
        length x = 10
        length y = 10
        
        # Resting-set Complexes 
        C = x( y( + b* ) ) a* 
        CR = x( y( + y b( + ) ) ) a* 
        CRF = x( y + y( b( + ) ) ) a* 
        L = a x 
        LC = a( x + x( y( + b* ) ) ) 
        LCF = a( x( + x y( + b* ) ) ) 
        LR = a( x( + y( b( + ) ) ) ) 
        R = y b 
        T = x y 
        
        # Transient Complexes 
        LCR = a( x + x( y( + y b( + ) ) ) ) 
        LCRF1 = a( x( + x y( + y b( + ) ) ) ) 
        LCRF2 = a( x + x( y + y( b( + ) ) ) ) 
        
        # Detailed Reactions 
        reaction [bind21         =      1.5e+06 /M/s ] C + L -> LC
        reaction [bind21         =      1.5e+06 /M/s ] C + R -> CR
        reaction [open           =           20 /s   ] CR -> C + R
        reaction [branch-3way    =           30 /s   ] CR -> CRF
        reaction [branch-3way    =           30 /s   ] CRF -> CR
        reaction [bind21         =      1.5e+06 /M/s ] L + CR -> LCR
        reaction [bind21         =      1.5e+06 /M/s ] L + CRF -> LCRF2
        reaction [open           =           20 /s   ] LC -> C + L
        reaction [branch-3way    =           30 /s   ] LC -> LCF
        reaction [branch-3way    =           30 /s   ] LCF -> LC
        reaction [branch-3way    =           30 /s   ] LCR -> LCRF1
        reaction [branch-3way    =           30 /s   ] LCR -> LCRF2
        reaction [branch-3way    =           30 /s   ] LCRF1 -> LCR
        reaction [branch-3way    =           30 /s   ] LCRF1 -> T + LR
        reaction [branch-3way    =           30 /s   ] LCRF2 -> LCR
        reaction [branch-3way    =           30 /s   ] LCRF2 -> T + LR
        reaction [bind21         =      1.5e+06 /M/s ] R + LC -> LCR
        reaction [bind21         =      1.5e+06 /M/s ] R + LCF -> LCRF1
        """)
        enum = Enumerator(complexes.values())
        enum.enumerate() 
        enumRG = PepperCondensation(enum)

        # TODO: It should saying here that the condensed graph is disconnected!
        self.assertEqual(list(enumRG.condensed_reactions), [])

    def test_fate_example(self):
        PepperComplex.PREFIX = 'enum'
        complexes, reactions = read_pil("""
        # File generated by peppercorn-v0.5.0

        # Domain Specifications 
        length a = 8
        length b = 8
        length c = 8
        length d2 = 8
        length d3 = 8
        length t = 4

        # Resting-set Complexes 
        e0 = d2( d3( + ) a* + a*( b*( c ) ) ) t* 
        e12 = d2 d3( + ) a* 
        e13 = t( d2( d3 + a*( b*( c ) ) ) ) 
        e21 = d2 d3 
        e22 = t( d2( d3( + ) a*( + a* b*( c ) ) ) ) 
        e27 = t( d2( d3( + ) a* + a*( b*( c ) ) ) ) 
        gate = d2( d3( + ) a*( + a* b*( c ) ) ) t* 
        t23 = t d2 d3 

        # Transient Complexes 
        e5 = t( d2 d3 + d2( d3( + ) a*( + a* b*( c ) ) ) ) 
        e7 = t( d2 d3 + d2( d3( + ) a* + a*( b*( c ) ) ) ) 
        e18 = t( d2( d3 + d2 d3( + ) a*( + a* b*( c ) ) ) ) 

        # Detailed Reactions 
        reaction [bind21         =      1.2e+06 /M/s ] e0 + t23 -> e7
        reaction [branch-3way    =     0.122307 /s   ] e0 -> gate
        reaction [branch-3way    =      41.6667 /s   ] e5 -> e7
        reaction [branch-3way    =      41.6667 /s   ] e5 -> e18
        reaction [open           =      306.345 /s   ] e5 -> t23 + gate
        reaction [open           =      306.345 /s   ] e7 -> e0 + t23
        reaction [branch-3way    =     0.122307 /s   ] e7 -> e5
        reaction [branch-3way    =      41.6667 /s   ] e7 -> e12 + e13
        reaction [branch-3way    =     0.122307 /s   ] e18 -> e5
        reaction [branch-3way    =      41.6667 /s   ] e18 -> e12 + e13
        reaction [branch-3way    =     0.122307 /s   ] e18 -> e22 + e21
        reaction [branch-3way    =      41.6667 /s   ] e22 -> e27
        reaction [branch-3way    =     0.122307 /s   ] e27 -> e22
        reaction [branch-3way    =      41.6667 /s   ] gate -> e0
        reaction [bind21         =      1.2e+06 /M/s ] t23 + gate -> e5
        """)
        gate = complexes['gate']
        t23 = complexes['t23']
        enum = Enumerator(complexes.values())
        enum.release_cutoff = 6
        enum.enumerate() # or enum.dry_run()
        self.assertEqual(sorted(enum.reactions), sorted(reactions))

        """
        # Resting sets 
        state re0 = [e0, gate]
        state re12 = [e12]
        state re13 = [e13]
        state re21 = [e21]
        state re22 = [e22, e27]
        state rt23 = [t23]

        reaction [condensed      =       287342 /M/s ] re0 + rt23 -> re13 + re12
        reaction [condensed      =      2.45499 /M/s ] re0 + rt23 -> re21 + re22
        """

        enumRG = PepperCondensation(enum)
        enumRG.condense()
        self.assertEqual(len(list(enumRG.resting_macrostates)), 6)
        self.assertEqual(len(list(enumRG.condensed_reactions)), 2)

    def test_sarma_fig4_v1(self):
        complexes, reactions = read_pil("""
        # File generated by peppercorn-v0.5.0

        # Domain Specifications 
        length d1 = 15
        length d2 = 15
        length d3 = 5
        length d4 = 15
        length d5 = 5
        length d6 = 15
        length d7 = 5

        # Resting-set Complexes 
        bot = d1* 
        com1 = d3*( d2*( d1*( d5 d6 + ) ) ) d4 
        com2 = d6( d7( + ) ) d5* d1 d2 d3 
        e6 = d1 d2 d3 d4 
        e11 = d6 d7 
        e17 = d7* d6*( d5*( d1( d2( d3( + ) ) ) ) ) 
        e27 = d1*( + ) 
        e29 = d1*( + d6( d7( + ) ) d5* ) d2 d3 
        e31 = d1*( + ) d2 d3 d4 
        top = d1 

        # Transient Complexes 
        e1 = d6( d7( + ) ) d5*( d1 d2 d3 + d1( d2( d3( d4 + ) ) ) ) d6 
        e7 = d6( d7( + ) ) d5*( d1( d2( d3( + ) ) ) ) d6 
        e8 = d6 d7( + ) d6*( d5*( d1 d2 d3 + d1( d2( d3( d4 + ) ) ) ) ) 
        e10 = d7* d6*( d5*( d1 d2 d3 + d1( d2( d3( d4 + ) ) ) ) ) 
        e15 = d6 d7( + ) d6*( d5*( d1( d2( d3( + ) ) ) ) ) 
        e33 = d6( d7( + ) ) d5*( d1( d2 d3 + ) + d1( d2( d3( d4 + ) ) ) ) d6 
        e37 = d6 d7( + ) d6*( d5*( d1( d2 d3 + ) + d1( d2( d3( d4 + ) ) ) ) ) 
        e38 = d6( d7( + ) ) d5*( d1( d2 d3 + d1*( + ) d2( d3( d4 + ) ) ) ) d6 
        e43 = d6 d7( + ) d6*( d5*( d1( d2 d3 + d1*( + ) d2( d3( d4 + ) ) ) ) ) 
        e47 = d7* d6*( d5*( d1( d2 d3 + d1*( + ) d2( d3( d4 + ) ) ) ) ) 
        e58 = d7* d6*( d5*( d1( d2 d3 + ) + d1( d2( d3( d4 + ) ) ) ) ) 

        # Detailed Reactions 
        reaction [bind21         =      4.5e+06 /M/s ] bot + top -> e27
        reaction [bind21         =      1.5e+06 /M/s ] com1 + e29 -> e33
        reaction [bind21         =      4.5e+06 /M/s ] com2 + bot -> e29
        reaction [bind21         =      1.5e+06 /M/s ] com2 + com1 -> e1
        reaction [open           =      21.7122 /s   ] e1 -> com2 + com1
        reaction [branch-3way    =      9.52381 /s   ] e1 -> e6 + e7
        reaction [branch-3way    =      22.2222 /s   ] e1 -> e8
        reaction [bind21         =      4.5e+06 /M/s ] e6 + bot -> e31
        reaction [branch-3way    =      22.2222 /s   ] e7 -> e15
        reaction [branch-3way    =      22.2222 /s   ] e8 -> e1
        reaction [branch-3way    =      9.52381 /s   ] e8 -> e6 + e15
        reaction [open           =      21.7122 /s   ] e8 -> e10 + e11
        reaction [branch-3way    =      9.52381 /s   ] e10 -> e6 + e17
        reaction [branch-3way    =      22.2222 /s   ] e15 -> e7
        reaction [open           =      21.7122 /s   ] e15 -> e17 + e11
        reaction [bind21         =      1.5e+06 /M/s ] e17 + e11 -> e15
        reaction [open           =      21.7122 /s   ] e33 -> com1 + e29
        reaction [branch-3way    =      22.2222 /s   ] e33 -> e37
        reaction [branch-4way    =  0.000623053 /s   ] e33 -> e38
        reaction [branch-3way    =      22.2222 /s   ] e37 -> e33
        reaction [branch-4way    =  0.000623053 /s   ] e37 -> e43
        reaction [open           =      21.7122 /s   ] e37 -> e58 + e11
        reaction [branch-3way    =      16.6667 /s   ] e38 -> e7 + e31
        reaction [branch-4way    =  0.000623053 /s   ] e38 -> e33
        reaction [branch-3way    =      22.2222 /s   ] e38 -> e43
        reaction [open           =      21.7122 /s   ] e43 -> e11 + e47
        reaction [branch-3way    =      16.6667 /s   ] e43 -> e15 + e31
        reaction [branch-4way    =  0.000623053 /s   ] e43 -> e37
        reaction [branch-3way    =      22.2222 /s   ] e43 -> e38
        reaction [branch-3way    =      16.6667 /s   ] e47 -> e17 + e31
        reaction [branch-4way    =  0.000623053 /s   ] e47 -> e58
        reaction [branch-4way    =  0.000623053 /s   ] e58 -> e47
        """)

        enum = Enumerator(complexes.values(), reactions)
        enum.enumerate() 
        self.assertEqual(sorted(enum.reactions), sorted(reactions))
        enumRG = PepperCondensation(enum)
        enumRG.condense()

@unittest.skipIf(SKIP, "skipping tests")
class CondenseCRNs(unittest.TestCase):
    def setUp(self):
        self.length = 1
        self.domain = PepperDomain('d1', dtype='short')
        self.complexes = dict()
        self.reactions = set()

    def tearDown(self):
        clear_memory()

    def cplx(self, name):
       """ Dummy function for generating formal species """
       name = name.strip()
       if name in self.complexes:
           return self.complexes[name]
       else:
           self.complexes[name] = PepperComplex(
                   [self.domain for x in range(self.length)],
                   list('.' * self.length), name=name)
           self.length +=1 
           return self.complexes[name]

    def rxn(self, string, k = 1, rtype = 'condensed'):
       """ Dummy function for generating reactions between formal species """
       reactants, products = string.split('->')
       reactants = reactants.split('+')
       products = products.split('+')

       reactants = [self.cplx(x) for x in reactants]
       products  = [self.cplx(x) for x in products]
       rxn = PepperReaction(reactants, products, rtype.strip())
       rxn.rate_constant = k
       self.reactions.add(rxn)

    def rs(self, names):
        return PepperMacrostate(list(map(self.cplx, names)))

    # Tests start here... 
    def test_CondenseGraphCRN_01(self):
        complexes = self.complexes
        reactions = self.reactions
        cplx = self.cplx
        rxn = self.rxn
        rs = self.rs

        rxn('A -> B + C')
        rxn('B -> D + E', k = 0.5)
        rxn('C -> F + G', k = 1)
        #rxn('B + C -> A') # raises error

        enum = Enumerator(list(complexes.values()), list(reactions))
        enum.dry_run()
        #for r in enum.reactions: print(r, r.rate)
        #print enum.complexes

        enumRG = PepperCondensation(enum)
        enumRG.condense()
        self.assertEqual(list(enumRG.condensed_reactions), [])
        self.assertEqual(sorted(enumRG.resting_macrostates), 
                sorted([rs('D'), rs('E'), rs('F'), rs('G')]))
        self.assertEqual(enumRG.complex_fates(cplx('A')), 
                         SetOfFates([[rs('D'), rs('E'), rs('F'), rs('G')]]))
 
    def test_CondenseGraphCRN_02(self):
        complexes = self.complexes
        reactions = self.reactions
        cplx = self.cplx
        rxn = self.rxn
        rs = self.rs

        rxn('A -> B')
        rxn('A -> C')
        rxn('B -> D')
        rxn('B -> E')
        rxn('C -> F')
        rxn('C -> G')

        enum = Enumerator(list(complexes.values()), list(reactions))
        enum.dry_run()

        enumRG = PepperCondensation(enum)
        enumRG.condense()
        self.assertEqual(sorted(enumRG.resting_macrostates), 
                sorted([rs('G'), rs('F'), rs('E'), rs('D')]))
        self.assertEqual(enumRG.complex_fates(cplx('A')),
                SetOfFates([[rs('D')], [rs('E')], [rs('F')], [rs('G')]]))
        self.assertEqual(enumRG.complex_fates(cplx('C')),
                SetOfFates([[rs('F')], [rs('G')]]))
        self.assertEqual(enumRG.complex_fates(cplx('F')),
                SetOfFates([[rs('F')]]))

    def test_CondenseGraphCRN_03(self):
        complexes = self.complexes
        reactions = self.reactions
        cplx = self.cplx
        rxn = self.rxn
        rs = self.rs

        rxn('X -> T1', k=0.1)
        rxn('T1 -> T2')
        rxn('T2 -> T1')
        rxn('T1 -> A')
        rxn('T1 -> B')
        rxn('T2 -> T3')
        rxn('T3 -> D')
        rxn('T3 -> C')

        enum = Enumerator(list(complexes.values()), list(reactions))
        enum.k_fast = 0.5
        enum.dry_run()

        enumRG = PepperCondensation(enum)
        enumRG.condense()

        self.assertEqual(sorted(enumRG.resting_macrostates), 
                sorted([rs('X'), rs('A'), rs('B'), rs('C'), rs('D')]))
 
        self.assertEqual(enumRG.complex_fates(cplx('X')),
                SetOfFates([[rs('X')]]))

        self.assertEqual(enumRG.complex_fates(cplx('T1')),
                SetOfFates([[rs('A')], [rs('B')], [rs('C')], [rs('D')]]))

    def test_sarma_fig4_CRN(self):
        complexes = self.complexes
        reactions = self.reactions
        cplx = self.cplx
        rxn = self.rxn
        rs = self.rs

        rxn('top + bot -> e27 ', k =    4.5e+06, rtype='bind21     ')
        rxn('com1 + e29 -> e33', k =    1.5e+06, rtype='bind21     ')
        rxn('bot + com2 -> e29', k =    4.5e+06, rtype='bind21     ')
        rxn('com1 + com2 -> e1', k =    1.5e+06, rtype='bind21     ')
        rxn('e1 -> com1 + com2', k =    21.7122, rtype='open       ')
        rxn('e1 -> e6 + e7    ', k =    9.52381, rtype='branch-3way')
        rxn('e1 -> e8         ', k =    22.2222, rtype='branch-3way')
        rxn('e6 + bot -> e31  ', k =    4.5e+06, rtype='bind21     ')
        rxn('e7 -> e15        ', k =    22.2222, rtype='branch-3way')
        rxn('e8 -> e1         ', k =    22.2222, rtype='branch-3way')
        rxn('e8 -> e6 + e15   ', k =    9.52381, rtype='branch-3way')
        rxn('e8 -> e10 + e11  ', k =    21.7122, rtype='open       ')
        rxn('e10 -> e6 + e17  ', k =    9.52381, rtype='branch-3way')
        rxn('e15 -> e7        ', k =    22.2222, rtype='branch-3way')
        rxn('e15 -> e17 + e11 ', k =    21.7122, rtype='open       ')
        rxn('e17 + e11 -> e15 ', k =    1.5e+06, rtype='bind21     ')
        rxn('e33 -> com1 + e29', k =    21.7122, rtype='open       ')
        rxn('e33 -> e37       ', k =    22.2222, rtype='branch-3way')
        rxn('e33 -> e38       ', k =0.000623053, rtype='branch-4way')
        rxn('e37 -> e33       ', k =    22.2222, rtype='branch-3way')
        rxn('e37 -> e43       ', k =0.000623053, rtype='branch-4way')
        rxn('e37 -> e58 + e11 ', k =    21.7122, rtype='open       ')
        rxn('e38 -> e31 + e7  ', k =    16.6667, rtype='branch-3way')
        rxn('e38 -> e33       ', k =0.000623053, rtype='branch-4way')
        rxn('e38 -> e43       ', k =    22.2222, rtype='branch-3way')
        rxn('e43 -> e47 + e11 ', k =    21.7122, rtype='open       ')
        rxn('e43 -> e31 + e15 ', k =    16.6667, rtype='branch-3way')
        rxn('e43 -> e37       ', k =0.000623053, rtype='branch-4way')
        rxn('e43 -> e38       ', k =    22.2222, rtype='branch-3way')
        rxn('e47 -> e31 + e17 ', k =    16.6667, rtype='branch-3way')
        rxn('e47 -> e58       ', k =0.000623053, rtype='branch-4way')
        rxn('e58 -> e47       ', k =0.000623053, rtype='branch-4way')

        enum = Enumerator(complexes.values(), reactions)
        enum.dry_run()

        enumRG = PepperCondensation(enum)
        enumRG.condense()

if __name__ == '__main__':
  unittest.main()

