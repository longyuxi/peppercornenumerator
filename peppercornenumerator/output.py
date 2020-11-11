#
#  peppercornenumerator/output.py
#  EnumeratorProject
#
import logging
log = logging.getLogger(__name__)

import xml.dom.minidom 
from itertools import chain
from collections import Counter

from . import __version__
from .utils import natural_sort, PeppercornUsageError

def write_pil(enumerator, fh = None, detailed = True, condensed = False, 
        molarity = 'nM', time = 's'):
    """Write the contents of :obj:`Enumerator()` into a *.pil file.

    Args:
      enumerator (:obj:`Enumerator()`): The enumertor object.
      fh (filehandle): The filehandle to which the output is written to. 
        If fh is None, then output is written to a string and returned.
      detailed (bool, optional): Print detailed CRN. Defaults to True.
      condensed (bool, optional): Print condensed CRN. Defaults to False.
    """

    out = []
    def output_string(string):
        if fh is None:
            out.append(string)
        else:
            fh.write(string)

    output_string("# File generated by peppercorn-{}\n".format(__version__))

    # Print domains
    seen = set()
    output_string("\n# Domains ({}) \n".format(len(list(enumerator.domains))))
    for dom in natural_sort(enumerator.domains):
        if dom.is_complement and not dom.sequence: 
            dom = ~dom
        if dom not in seen:
            if dom.sequence:
                output_string("sequence {:s} = {} : {:d}\n".format(
                    dom.name, dom.sequence, len(dom)))
            else:
                output_string("length {:s} = {:d}\n".format(dom.name, len(dom)))
            seen.add(dom)

    unused = set(enumerator.named_complexes) - set(enumerator.complexes)
    strands = [u for u in unused if u.structure is None]
    unused = [u for u in unused if u.structure]
    if strands:
        output_string(f"\n# Input strands or composite domains ({len(strands)}) \n")
        for cplx in natural_sort(strands):
            output_string("sup-sequence {:s} = {:s}\n".format(
                cplx.name, ' '.join([d.name for d in cplx.sequence])))

    if unused:
        output_string("\n# Not enumerated input complexes ({}) \n".format(len(unused)))
        for cplx in natural_sort(unused):
            assert cplx.concentration is not None
            output_string("{:s} = {:s} @{} {} {}\n".format(cplx.name, 
                cplx.kernel_string, *cplx.concentrationformat(molarity)))

    # Print resting complexes
    output_string("\n# Resting complexes ({}) \n".format(len(list(enumerator.resting_complexes))))
    for cplx in natural_sort(enumerator.resting_complexes):
        if cplx.concentration:
            output_string("{:s} = {:s} @{} {} {}\n".format(cplx.name, 
                cplx.kernel_string, *cplx.concentrationformat(molarity)))
        else:
            output_string("{:s} = {:s}\n".format(cplx.name, cplx.kernel_string))
 
    if condensed:
        # Print resting macrostates
        output_string("\n# Resting macrostates ({}) \n".format(
            len(list(enumerator.resting_macrostates))))
        for resting in natural_sort(enumerator.resting_macrostates):
            output_string("macrostate {:s} = [{:s}]\n".format(str(resting), 
                ', '.join(map(str,resting.complexes))))

        # Print reactions
        output_string("\n# Condensed reactions ({}) \n".format(len(list(enumerator.condensed_reactions))))
        for rxn in natural_sort(enumerator.condensed_reactions):
            rxn.rate_constant = rxn.rateformat(f'/{molarity}' * (rxn.arity[0] - 1) + f'/{time}')
            output_string(f"{rxn.reaction_string}\n")

    if detailed:
        # Print transient complexes
        output_string("\n# Transient complexes ({}) \n".format(len(list(enumerator.transient_complexes))))
        for cplx in natural_sort(enumerator.transient_complexes):
            if cplx._concentration:
                output_string("{:s} = {:s} @{} {} {}\n".format(cplx.name, cplx.kernel_string, 
                    *cplx.concentrationformat(molarity)))
            else:
                output_string("{:s} = {:s}\n".format(cplx.name, cplx.kernel_string))

        # Print reactions
        output_string("\n# Detailed reactions ({}) \n".format(len(list(enumerator.reactions))))
        for rxn in natural_sort(enumerator.reactions):
            rxn.rate_constant = rxn.rateformat(f'/{molarity}' * (rxn.arity[0] - 1) + f'/{time}')
            output_string(f"{rxn.reaction_string}\n")
    return ''.join(out)

def write_crn(enumerator, fh = None, condensed = False, molarity = 'nM', time = 's'):
    out = []
    def output_string(string):
        if fh is None:
            out.append(string)
        else:
            fh.write(string)
    output_string(f"# File generated by peppercorn-{__version__}\n")
    if condensed:
        output_string(f"\n# Condensed reactions: concentration = {molarity}, time = {time}\n")
        for rxn in natural_sort(enumerator.condensed_reactions):
            rxn.rate_constant = rxn.rateformat(f'/{molarity}' * (rxn.arity[0] - 1) + f'/{time}')
            output_string('{} -> {} [k = {}]\n'.format(' + '.join(map(str, rxn.reactants)), 
                                                     ' + '.join(map(str, rxn.products)),
                                                     rxn.rate_constant[0]))
    else:
        output_string(f"\n# Detailed reactions: concentration = {molarity}, time = {time}\n")
        for rxn in natural_sort(enumerator.reactions):
            rxn.rate_constant = rxn.rateformat(f'/{molarity}' * (rxn.arity[0] - 1) + f'/{time}')
            output_string('{} -> {} [k = {}]\n'.format(' + '.join(map(str, rxn.reactants)), 
                                                     ' + '.join(map(str, rxn.products)),
                                                     rxn.rate_constant[0]))
    return ''.join(out)


def write_vdsd(enumerator, fh = None, detailed = True, condensed = False):
    """ Write an Enumerator Object into VisualDSD *.crn format.

    directive simulation {plots=[sp_0; sp_1; sp_2; sp_3; sp_4; sp_5; sp_6; sp_7; sp_8; sp_9; sp_10]; }

    | 10 sp_0
    | 100 sp_1
    | sp_1 <->{displace}{displace} sp_10
    | sp_9 ->{displace} sp_7 + sp_6
    | sp_0 + sp_1 <->{bind}{unbind} sp_9
    | sp_9 <->{displace}{displace} sp_8
    | sp_0 + sp_10 <->{bind}{unbind} sp_8
    | sp_5 ->{displace} sp_7 + sp_6
    | sp_8 <->{displace}{displace} sp_5
    | sp_5 ->{displace} sp_4 + sp_3
    | sp_3 <->{displace}{displace} sp_2

    Args:
      fh (filehandle): The function prints to this filehandle.
      ...
    
    directive simulator deterministic
    directive simulator cme
    directive stochastic { scale = 1 }

    directive simulation {
        initial=0.0; 
        final=6000.0; 
        points=1000; 
        plots=[Signal]
    }

    directive inference { 
        burnin = 1000; 
        samples = 5000; 
        thin = 100 
    }

    directive parameters [
      k=0.0003, {distribution=Uniform(1E-05, 0.002); interval=Log; variation=Random};
      bad=0.2, {distribution=Uniform(0.0, 0.3); interval=Real; variation=Random};
      T1=600.0, {distribution=Uniform(0.0, 1800.0); interval=Real;  variation=Random};
      N = 0.6;
    ]
    """

    if detailed == condensed:
        raise PeppercornUsageError('Choose either detailed or condensed for vdsd output.')

    if detailed:
        complexes = natural_sort(enumerator.resting_complexes) + \
                    natural_sort(enumerator.transient_complexes)
    else:
        complexes = natural_sort(enumerator.resting_macrostates)

    def logicDSD(cplx):
        """Translates a complex sequence / structure into LogicDSD notation."""
        seq = cplx.sequence
        dpp = cplx.structure
        lst = [str(d) for d in seq]
        stack, c = [], 1
        for i, (dom, pair) in enumerate(zip(seq, dpp)):
            if pair == '.':
                assert lst[i] == str(dom)
                if dom.dtype == 'short':
                    lst[i] = dom.name[:-1]+'^*' if dom.name[-1] == '*' else str(dom)+'^'
            elif pair == '+':
                assert lst[i] == '+'
                lst[i] = '> | <'
            elif pair == '(':
                assert lst[i] == str(dom)
                if dom.dtype == 'short':
                    lst[i] = dom.name[:-1]+'^*' if dom.name[-1] == '*' else str(dom)+'^'
                stack.append(i)
            elif pair == ')':
                assert lst[i] == str(dom)
                if dom.dtype == 'short':
                    lst[i] = dom.name[:-1]+'^*' if dom.name[-1] == '*' else str(dom)+'^'
                try:
                    j = stack.pop()
                except IndexError as e:
                    raise NuskellObjectError(
                        "Too many closing brackets in secondary structure")
                lst[i] += '!' + str(c)
                lst[j] += '!' + str(c)
                c += 1
            else:
                raise PeppercornUsageError(f'weird character: {pair}')
        return "< {:s} >".format(' '.join(lst))

    out = []
    def output_string(string):
        if fh is None:
            out.append(string)
        else:
            fh.write(string)

    output_string(f"(* File autogenerated by peppercorn-{__version__} *)\n\n")

    #t0, t8, tnum = 0, 10, 100
    output_string("directive simulation {\n" + 
            #"   initial={:.2f};\n".format(t0) + 
            #"   final={:d};\n".format(t8) +
            #"   points={:d};\n".format(tnum) +
            "   plots=[{:s}];\n}}\n\n".format(
                "; ".join(map(str, complexes))))
 
    #output_string("directive stochastic {scale = 1}\n\n")
    #output_string("directive simulator cme\n\n")
    
    output_string("(* LogicDSD species:\n")
    for cplx in complexes:
        if condensed: cplx = cplx.representative
        output_string("{:s} = {:s}\n".format(cplx.name, logicDSD(cplx)))
    output_string("*)\n\n")

    if condensed:
        # Print resting macrostates
        output_string("\n(* Resting macrostate concentrations ({}) *)\n".format(len(complexes)))

        for resting in complexes:
            clist = [c.concentrationformat('nM')[1] \
                    for c in resting.complexes if c.concentration is not None]
            mconc = sum(clist)
            if mconc:
                output_string("| {:d} {:s}\n".format(int(mconc), resting.representative.name))
            elif len(clist) < len(resting):
                output_string("| {:d} {:s}\n".format(1, resting.representative.name))

        # Print reactions
        output_string("\n(* Condensed reactions ({}) *)\n".format(
            len(list(enumerator.condensed_reactions))))
        for rxn in natural_sort(enumerator.condensed_reactions):
            rxn.rate_constant = rxn.rateformat(f'/nM' * (rxn.arity[0] - 1) + f'/s')
            output_string("| {:s} -> {{{:g}}} {:s}\n".format(
                ' + '.join(map(str, rxn.reactants)), rxn.rate_constant[0], 
                ' + '.join(map(str, rxn.products))))

    else:
        # Print resting and transient complexes
        output_string("(* Initial complex concentrations ({}) *)\n".format(len(complexes)))
        for cplx in complexes:
            if cplx.concentration and cplx.concentration[1]:
                output_string("| {:d} {:s}\n".format(
                    cplx.concentrationformat('nM')[1], cplx.name))
            else:
                output_string("| {:d} {:s}\n".format(1, cplx.name))

        # Print reactions
        output_string("\n(* Detailed reactions ({}) *)\n".format(len(list(enumerator.reactions))))
        for rxn in natural_sort(enumerator.reactions):
            rxn.rate_constant = rxn.rateformat(f'/nM' * (rxn.arity[0] - 1) + f'/s')
            output_string("| {:s} -> {{{:g}}} {:s}\n".format(
                ' + '.join(map(str, rxn.reactants)), rxn.rate_constant[0], 
                ' + '.join(map(str, rxn.products))))

    return ''.join(out)

def write_sbml(enumerator, fh = None, condensed = False, compartment = 'TestTube'):
    """ Export reaction system to SBML Version 3 Lvl 2:

    Potentially useful links ...
        http://sbml.org/Documents/Specifications
        https://github.com/matthiaskoenig/sbmlutils
        https://sys-bio.github.io/roadrunner/python_docs/introduction.html
    """
    molarity = 'M' # as opposed to nM, uM, mM, etc; [mole / liter]
    time = 's'
    volume = 1 # 1.66 * 1e-15 # liter 

    if molarity != 'M':
        log.error('M is currently the only supported concentration format for SBML.')
        molarity = 'M'

    if time != 's':
        log.error('Seconds (s) is currently the only supported time unit for SBML.')
        time = 's'

    max_rar = 2 # Determine maximum number of reactants to define global units later ...
    reactions = list(enumerator.condensed_reactions) if condensed else list(enumerator.reactions)
    for rxn in reactions:
        rar = rxn.arity[0] - 1
        if rar > max_rar:
            max_rar = rar

    # -----------------
    # Helper functions:
    # -----------------
    def xml_list_of_species():
        # Returs species in counts [mole], not concentration [mole/liter]
        def xml_species(name, init, unit):
            assert unit == "mole"
            return """<species compartment="{:s}" id="{:s}" initialAmount="{:g}" 
                            boundaryCondition="false" hasOnlySubstanceUnits="false" 
                            substanceUnits="mole" constant="false"/>""".format(
                                    compartment, name, init, unit)
        xml = ''
        if condensed:
            for rm in enumerator.resting_macrostates:
                mole_list = [c.concentrationformat(molarity)[1] * volume \
                         for c in rm.complexes if c.concentration is not None]
                moles = sum(mole_list) # if sum(clist) else 0.0 # if else needed?
                xml += xml_species(rm.representative.name, moles, 'mole')
        else:
            for cplx in chain(enumerator.resting_complexes, enumerator.transient_complexes):
                moles = cplx.concentrationformat(molarity)[1] * volume if \
                        cplx.concentration else 0.0
                xml += xml_species(cplx.name, moles, 'mole')
        return xml

    def xml_list_of_reactions():
        # Returns rate constants in /s, /M/s, /M/M/s, ... to yield rates in M/s (= mole/L/s)
        def xml_species(name, count):
            return '<speciesReference species="{:s}" stoichiometry="{:d}" constant="true"/>'.format(
                    name, count)
        def xml_reaction(rxn):
            reactants = Counter([str(s) for s in rxn.reactants])
            products = Counter([str(s) for s in rxn.products])
            reac = '\n'.join([xml_species(k,v) for k,v in reactants.items()])
            prod = '\n'.join([xml_species(k,v) for k,v in products.items()])

            rxnID = '{}__{}'.format('_'.join(reactants.elements()),'_'.join(products.elements()))
            
            law = '<apply> <times/> <ci>k</ci> {:s} </apply>'.format(
                        ' '.join(['<ci>{:s}</ci>'.format(e) for e in reactants.elements()]))

            # /M ... /sec
            ratec = rxn.rateformat(f'/{molarity}' * (rxn.arity[0] - 1) + f'/{time}')[0] 
            txtunits = 'per_molar_' * rar + 'per_second'
            par = '<localParameter id="k" value="{:g}" units="{:s}"/>'.format(ratec, txtunits)

            return """
                <reaction id="{:s}" reversible="false">
                    <listOfReactants>
                        {:s}
                    </listOfReactants>
                    <listOfProducts>
                        {:s}
                    </listOfProducts>
                    <kineticLaw>
                        <math xmlns="http://www.w3.org/1998/Math/MathML">
                        <apply> <times/> <ci>{:s}</ci> 
                            {:s}
                        </apply>
                        </math>
                        <listOfLocalParameters>
                            {:s}
                        </listOfLocalParameters>
                    </kineticLaw>
                </reaction>
                """.format(rxnID, reac, prod, compartment, law, par)
        xml = ''
        reactions = enumerator.condensed_reactions if condensed else enumerator.reactions
        for rxn in reactions:
            xml += xml_reaction(rxn)
        return xml

    def xml_list_of_units(max_reactants):
        def unit_definition(rar):
            txtunits = 'per_molar_' * rar + 'per_second'
            return """
                    <unitDefinition id="{:s}">
                        <listOfUnits>
                        <unit kind="mole" exponent="-{:d}" scale="0" multiplier="1"/>
                        <unit kind="litre" exponent="{:d}" scale="0" multiplier="1"/>
                        <unit kind="second" exponent="-1" scale="0" multiplier="1"/>
                        </listOfUnits>
                    </unitDefinition>
                    """.format(txtunits, rar, rar)
        xml = ''
        for e in range(1, max_reactants + 1):
            xml += unit_definition(e)
        return xml

    # Ok, so let's set this up ...
    xmlspex = """
    <sbml xmlns="http://www.sbml.org/sbml/level3/version2/core" level="3" version="2">
    <model extentUnits="mole" timeUnits="second">
        <listOfUnitDefinitions>
            <unitDefinition id="per_second">
                <listOfUnits>
                    <unit kind="second" exponent="-1" scale="0" multiplier="1"/>
                </listOfUnits>
            </unitDefinition>
            {:s}
        </listOfUnitDefinitions>
        <listOfCompartments>
            <compartment id="{:s}" 
                size="{:g}" spatialDimensions="3" units="litre" constant="true"/>
        </listOfCompartments>
        <listOfSpecies>
            {:s}
        </listOfSpecies>
        <listOfReactions>
            {:s}
        </listOfReactions>
    </model>
    </sbml>
    """.format(xml_list_of_units(max_rar), compartment, volume, xml_list_of_species(), xml_list_of_reactions())

    doc = xml.dom.minidom.parseString(xmlspex)
    doc = doc.toprettyxml(indent = ' ', encoding="UTF-8")
    doc = '\n'.join([s.decode() for s in doc.splitlines() if s.strip()]) + '\n'

    if fh:
        fh.write(doc)
    return '' if fh else doc

