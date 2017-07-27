#
#  enumerator.py
#  EnumeratorProject
#
#  Created by Karthik Sarma on 4/18/10.
#

import sys
import logging
import itertools

import peppercornenumerator.utils as utils
import peppercornenumerator.reactions as reactions


# These are sanity checks to prevent infinite looping
MAX_COMPLEX_SIZE = 6
MAX_REACTION_COUNT = 1000
MAX_COMPLEX_COUNT = 200

# There should be better control of this limit -- only set it when
# necessary (Erik Winfree based on Chris Thachuk's advice...)
sys.setrecursionlimit(20000)


fast_reactions = {1: [reactions.bind11, reactions.open,
                      reactions.branch_3way, reactions.branch_4way]}
"""
Dictionary of reaction functions considered *fast* for a given "arity".
Keys are arities (e.g. 1 = unimolecular, 2 = bimolecular, 3 = trimolecular,
etc.), and values are lists of reaction functions. Currently, only
unimolecular fast reactions (arity = 1) are supported.
"""

slow_reactions = {
    1: [],
    2: [reactions.bind21]
}
"""
Similar to :py:func:`.fast_reactions` above,
a dictionary of reaction functions considered *slow* for a given "arity".
Keys are arities (e.g. 1 = unimolecular, 2 = bimolecular, 3 = trimolecular,
etc.), and values are lists of reaction functions. Currently, only
unimolecular fast reactions (arity = 1) are supported.
Slow reactions can only be unimolecular or bimolecular, though
:py:func:`Enumerator.make_slow_reactions` below could be changed in
order to lift this restriction.
"""

class PolymerizationError(Exception):
    """Error class to catch polymerization."""

    def __init__(self, msg, val=None):
        self.message = msg
        if val :
            self.message += " ({})".format(val)
        super(PolymerizationError, self).__init__(self.message) 


class Enumerator(object):
    """
    Represents a single enumerator instance, consisting of all the information
    required for a reaction graph. This class is the coordinator for the state
    enumerator. Enumerators have immutable starting conditions. If unzip is true,
    all 3-way branch migrations are greedy.
    """

    def __init__(self, domains, strands, initial_complexes):
        """
        Initializes the enumerator. Takes a list of domains, a list of strands
        made up of those domains, and a list of the initial complexes, made
        of the strands.

        :param list domains: Domain objects in the ensemble
        :param list strands: Strand objects in the ensemble
        :param list initial_complexes: Complex objects in the system starting configuration.
        """
        self._domains = domains
        self._strands = strands
        self._initial_complexes = initial_complexes
        self._reactions = None
        self._resting_states = None
        self._complexes = None
        self._transient_complexes = None
        self._resting_complexes = None

        global MAX_COMPLEX_SIZE
        global MAX_REACTION_COUNT
        global MAX_COMPLEX_COUNT
        self.MAX_COMPLEX_SIZE = MAX_COMPLEX_SIZE
        self.MAX_REACTION_COUNT = MAX_REACTION_COUNT
        self.MAX_COMPLEX_COUNT = MAX_COMPLEX_COUNT
        self.DFS = True
        self.FAST_REACTIONS = fast_reactions[1]
        self.interruptible = True
        self.interactive = False
        self.k_slow = 0  # float("-inf")
        self.k_fast = 0  # float("-inf")

    @property
    def auto_name(self):
        return reactions.auto_name

    def get_auto_name(self):
        return reactions.get_auto_name()

    @property
    def domains(self):
        return self._domains[:]

    @property
    def strands(self):
        return self._strands[:]

    @property
    def initial_complexes(self):
        """
        Complexes present in the system's initial configuration
        """
        return self._initial_complexes[:]

    @property
    def reactions(self):
        """
        List of reactions enumerated. :py:meth:`.enumerate` must be
        called before access.
        """
        if self._reactions is None:
            raise utils.PeppercornUsageError("enumerate not yet called!")
        return self._reactions[:]

    @property
    def resting_states(self):
        """
        List of resting states enumerated. :py:meth:`.enumerate` must be
        called before access.
        """
        if self._resting_states is None:
            raise utils.PeppercornUsageError("enumerate not yet called!")
        return self._resting_states[:]

    @property
    def complexes(self):
        """
        List of complexes enumerated. :py:meth:`.enumerate` must be
        called before access.
        """
        if self._complexes is None:
            raise utils.PeppercornUsageError("enumerate not yet called!")
        return self._complexes[:]

    @property
    def resting_complexes(self):
        """
        List of complexes enumerated that are within resting states.
        :py:meth:`.enumerate` must be called before access.
        """
        if self._resting_complexes is None:
            raise utils.PeppercornUsageError("enumerate not yet called!")
        return self._resting_complexes[:]

    @property
    def transient_complexes(self):
        """
        List of complexes enumerated that are not within resting states (e.g.
        complexes which are transient). :py:meth:`.enumerate` must be
        called before access.
        """
        if self._transient_complexes is None:
            raise utils.PeppercornUsageError("enumerate not yet called!")
        return self._transient_complexes[:]

    def __eq__(self, object):
        return (sorted(self.domains) == sorted(object.domains)) and \
            (sorted(self.strands) == sorted(object.strands)) and \
            (sorted(self.initial_complexes) == sorted(object.initial_complexes)) and \
            (sorted(self.reactions) == sorted(object.reactions)) and \
            (sorted(self.resting_states) == sorted(object.resting_states)) and \
            (sorted(self.complexes) == sorted(object.complexes)) and \
            (sorted(self.resting_complexes) == sorted(object.resting_complexes)) and \
            (sorted(self.transient_complexes) ==
             sorted(object.transient_complexes))

    def dry_run(self):
        """
        Make it look like you've enumerated, but actually do nothing.
        """
        self._complexes = self.initial_complexes[:]
        self._resting_complexes = self._complexes[:]
        self._resting_states = [utils.RestingState(
            complex.name, [complex]) for complex in self._complexes]
        self._transient_complexes = []
        self._reactions = []

    def set_reaction_options(self):
        # handle release cutoff
        self.old = {}
        self.old['release_cutoff_1_1'] = reactions.RELEASE_CUTOFF_1_1
        self.old['release_cutoff_1_N'] = reactions.RELEASE_CUTOFF_1_N
        self.old['unzip'] = reactions.UNZIP
        self.old['legacy_unzip'] = reactions.LEGACY_UNZIP
        self.old['reject_remote'] = reactions.REJECT_REMOTE
        if (hasattr(self, 'RELEASE_CUTOFF')):
            reactions.RELEASE_CUTOFF_1_1 = self.RELEASE_CUTOFF
            reactions.RELEASE_CUTOFF_1_N = self.RELEASE_CUTOFF

        if (hasattr(self, 'RELEASE_CUTOFF_1_1')):
            reactions.RELEASE_CUTOFF_1_1 = self.RELEASE_CUTOFF_1_1

        if (hasattr(self, 'RELEASE_CUTOFF_1_N')):
            reactions.RELEASE_CUTOFF_1_N = self.RELEASE_CUTOFF_1_N

        if (hasattr(self, 'UNZIP')):
            reactions.UNZIP = self.UNZIP
            if reactions.UNZIP:
                logging.info("Using max-helix semantics")

        if (hasattr(self, 'LEGACY_UNZIP')):
            reactions.LEGACY_UNZIP = self.LEGACY_UNZIP
            if reactions.LEGACY_UNZIP:
                logging.info("Using legacy unzipping mode")
            if not reactions.UNZIP:
                logging.debug(
                    "Note: legacy unzip mode will have no effect, since max helix semantics are disabled")

        if (hasattr(self, 'REJECT_REMOTE')):
            reactions.REJECT_REMOTE = self.REJECT_REMOTE
            if reactions.REJECT_REMOTE:
                logging.info(
                    "Ignoring remote toehold-mediated branch migration")

    def reset_reaction_options(self):
        reactions.RELEASE_CUTOFF_1_1 = self.old['release_cutoff_1_1']
        reactions.RELEASE_CUTOFF_1_N = self.old['release_cutoff_1_N']
        reactions.UNZIP = self.old['unzip']
        reactions.LEGACY_UNZIP = self.old['legacy_unzip']
        reactions.REJECT_REMOTE = self.old['reject_remote']

    def enumerate(self):
        """
        Generates the reaction graph consisting of all complexes reachable from
        the initial set of complexes. Produces a full list of :py:meth:`complexes`, resting
        states, and :py:meth:`reactions, which are stored in the associated members of this
        class.
        """

        self.set_reaction_options()
        logging.info("Release cutoff 1-1: %d nt" %
                     reactions.RELEASE_CUTOFF_1_1)
        logging.info("Release cutoff 1-n: %d nt" %
                     reactions.RELEASE_CUTOFF_1_N)

        # Will be called once enumeration halts, either because it's finished or
        # because too many complexes/reactions have been enumerated
        def finish(premature=False):
            self.reset_reaction_options()

            # copy E and T into #complexes
            self._complexes += (self._E)
            self._complexes += (self._T)

            # preserve resting and transient complexes separately
            self._transient_complexes = self._T
            self._resting_complexes = self._E

            # If we're bailing because of too many reactions or complexes, search
            # self._reactions to ensure there are no reactions which contain
            # products that never made it into self._complexes
            # TODO: this is ugly and Om(n*m*p)... should we just go thru self._B
            # and try to classify?
            if premature:
                self._resting_complexes += self._S
                self._complexes += self._S
                complexes = set(self._complexes)

                new_reactions = []
                for reaction in self.reactions:
                    reaction_ok = all(
                        (product in complexes) for product in reaction.products) and all(
                        (reactant in complexes) for reactant in reaction.reactants)

                    # reaction_ok = True
                    # for product in reaction.products:
                    # 	#if (product in self._B) and not (product in self._complexes):
                    # 	if not (product in self._complexes):
                    # 		reaction_ok = False

                    if reaction_ok:
                        new_reactions.append(reaction)

                self._reactions = new_reactions

        # List E contains enumerated resting state complexes. Only cross-
        # reactions  with other end states need to be considered for these
        # complexes. These complexes will remain in this list throughout
        # function execution.
        self._E = []

        # List S contains resting state complexes which have not yet had cross-
        # reactions with set E enumerated yet. All self-interactions for these
        # complexes have been enumerated
        self._S = []

        # List T contains transient states which have had their self-reactions
        # enumerated. These complexes will remain in this list throughout
        # function execution.
        self._T = []

        # List N contains self-enumerated components of the current
        # 'neighborhood'---consisting of states which are connected via fast
        # reactions to the current complex of interest, but have not yet been
        # characterized as transient or resting states.
        self._N = []

        # List F contains components of the current 'neighborhood' which have
        # not yet had their self-reactions enumerated. They will be moved to N
        # when they are enumerated.
        self._F = []

        # List B contains products of bimolecular reactions that have had no
        # reactions enumerated yet. They will be moved to F when their
        # 'neighborhood' is to be considered.
        self._B = self.initial_complexes[:]

        self._reactions = []
        self._complexes = []
        self._resting_states = []

        def do_enumerate():

            # We first generate the states reachable by fast reactions from the
            # initial complexes
            logging.debug("Fast reactions from initial complexes...")
            while len(self._B) > 0:
                # Generate a neighborhood from `source`
                source = self._B.pop()
                self.process_neighborhood(source)

            # Consider slow reactions between resting state complexes
            logging.debug("Slow reactions between resting state complexes...")
            while len(self._S) > 0:

                # Find slow reactions from `element`
                if self.DFS:
                    element = self._S.pop()
                else:
                    element = self._S.pop(0)

                logging.debug(
                    "Slow reactions from complex %s (%d remaining in S)" %
                    (element, len(
                        self._S)))
                slow_reactions = self.get_slow_reactions(element)
                self._E.append(element)

                # Find the new complexes which were generated
                self._B = self.get_new_products(slow_reactions)
                self._reactions += (slow_reactions)
                logging.debug("Generated %d new slow reactions" %
                              len(slow_reactions))
                logging.debug("Generated %d new products" % len(self._B))

                # Display new reactions in interactive mode
                self.reactions_interactive(element, slow_reactions, 'slow')

                # Now find all complexes reachable by fast reactions from these
                # new complexes
                while len(self._B) > 0:

                    # Check whether too many complexes have been generated
                    if (len(self._E) + len(self._T) + len(self._S) > self.MAX_COMPLEX_COUNT):
                        raise PolymerizationError("Too many complexes enumerated!", 
                                len(self._E) + len(self._T) + len(self._S))

                    # Check whether too many reactions have been generated
                    if (len(self._reactions) > self.MAX_REACTION_COUNT):
                        raise PolymerizationError("Too many reactions enumerated!", 
                                len(self._reactions))

                    # Generate a neighborhood from `source`
                    source = self._B.pop()
                    self.process_neighborhood(source)

        if self.interruptible:
            try:
                do_enumerate()
            except KeyboardInterrupt:
                logging.warning("Interrupted; gracefully exiting...")
                finish(premature=True)
            except PolymerizationError as e:
                logging.exception(e)
                # print e
                # import traceback
                # print traceback.format_exc()
                logging.warning("Polymerization error; gracefully exiting...")
                finish(premature=True)
        else:
            do_enumerate()

        finish()

    def reactions_interactive(self, root, reactions, type='fast'):
        """
        Prints the passed reactions as a kernel string, then waits for keyboard
        input before continuing.
        """
        if self.interactive:
            print "%s = %s (%s)" % (root.name, root.kernel_string(), type)
            print
            for r in reactions:
                print r.kernel_string()
            if len(reactions) is 0:
                print "(No %s reactions)" % type
            print
            utils.wait_for_input()

    # def partition_reactions(self, reactions):
    # 	too_slow = []
    # 	slow = []
    # 	fast = []

    # 	for r in self.reactions:
    # 		if r.rate() < self.k_slow: too_slow.append(r)
    # 		elif self.k_slow < r.rate() < self.k_fast: slow.append(r)
    # 		elif self.k_fast < r.rate(): fast.append(r)
    # 		else:
    # 			raise Exception("Unable to classify reaction as fast (k > %(k_fast)d) or slow (%(k_slow)d > k > %(k_fast)d)" % { k_slow: self.k_slow, k_fast: self.k_fast })

    # 	return (too_slow, slow, fast)

    def process_neighborhood(self, source):
        """
        Takes a single complex, generates the 'neighborhood' of complexes
        reachable from that complex through fast reactions, classifies these
        complexes as transient or resting state, and modifies the lists and
        list of reactions accordingly.

        :param utils.Complex source: Complex from which to generate a neighborhood
        """

        # N_reactions holds reactions which are part of the current
        # neighborhood
        N_reactions = []

        # N_reactions_fast = []
        # N_reactions_slow = []

        self._F = [source]

        logging.debug("Processing neighborhood: %s" % source)

        try:

            # First find all of the complexes accessible through fast
            # reactions starting with the source
            while (len(self._F) > 0):

                # Find fast reactions from `element`
                element = self._F.pop()
                logging.debug(
                    "Fast reactions from %s... (%d remaining in F)" %
                    (element, len(
                        self._F)))
                reactions = self.get_fast_reactions(element)

                # # Partition reactions into too slow (discard), slow, and fast
                # reactions_too_slow, reactions_slow, reactions_fast = self.partition_reactions(reactions)

                # Add new products to F
                new_products = self.get_new_products(reactions)
                # new_products = self.get_new_products(reactions_fast)
                self._F += (new_products)

                # Add new reactions to N_reactions
                N_reactions += (reactions)
                # N_reactions_fast += reactions_fast
                # N_reactions_slow += reactions_slow
                self._N.append(element)

                logging.debug("Generated %d new fast reactions" %
                              len(reactions))
                logging.debug("Generated %d new products" % len(new_products))

                # Display new reactions in interactive mode
                self.reactions_interactive(element, reactions, 'fast')

        except KeyboardInterrupt:
            logging.debug("Exiting neighborhood %s prematurely..." % source)

        finally:

            logging.debug("In neighborhood %s..." % source)
            logging.debug("Segmenting %d complexes and %d reactions" %
                          (len(self._N), len(N_reactions)))

            # Now segment the neighborhood into transient and resting states
            # by finding the strongly connected components
            segmented_neighborhood = self.segment_neighborhood(
                self._N, N_reactions)
            # segmented_neighborhood = self.segment_neighborhood(self._N, N_reactions_fast)

            # Resting state complexes are added to S
            self._S += (segmented_neighborhood['resting_state_complexes'])

            # Transient state complexes are added to T
            self._T += (segmented_neighborhood['transient_state_complexes'])

            # Resting states are added to the list
            self._resting_states += (segmented_neighborhood['resting_states'])

            # # Filter slow reactions to only include those whose reactants are resting set complexes
            # S = set(self._S)
            # N_reactions_slow = [r for r in N_reactions_slow if all(x in S for x in r.reactants)]

            # Reactions from this neighborhood are added to the list
            # N_reactions = N_reactions_fast # + N_reactions_slow
            self._reactions += (N_reactions)

            # Reset neighborhood
            self._N = []
            logging.debug("Generated %d new fast reactions" % len(N_reactions))
            logging.debug(
                "Generated %d new products (%d transients, %d resting complexes)" %
                (len(
                    self._N), len(
                    segmented_neighborhood['transient_state_complexes']), len(
                    segmented_neighborhood['resting_state_complexes'])))
            logging.debug("Generated %d resting states" %
                          len(segmented_neighborhood['resting_states']))
            logging.debug("Done processing neighborhood: %s" % source)

    def get_slow_reactions(self, complex):
        """
        Returns a list of slow reactions possible using complex and other
        complexes in list E as reagents.

        This only supports unimolecular and bimolecular reactions. Could be
        extended to support arbitrary reactions.
        """

        reactions = []

        # Do unimolecular reactions that are always slow
        for move in slow_reactions[1]:
            reactions += (move(complex))

        # Do unimolecular reactions that are sometimes slow
        for move in self.FAST_REACTIONS:
            move_reactions = move(complex)
            reactions += (r for r in move_reactions if self.k_fast >
                          r.rate() > self.k_slow)

        # Do bimolecular reactions
        for move in slow_reactions[2]:
            reactions += (move(complex, complex))
            for complex2 in self._E:
                reactions += (move(complex, complex2))

        return reactions

    def get_fast_reactions(self, complex):
        """
        Returns a list of fast reactions possible using complex as a reagent.

        This only supports unimolecular reactions. Could be extended to support
        arbitrary reactions.
        """

        reactions = []

        # Do unimolecular reactions
        for move in self.FAST_REACTIONS:
            move_reactions = move(complex)
            # reactions += (r for r in move_reactions if r.rate() > self.k_slow)
            reactions += (r for r in move_reactions if r.rate() > self.k_fast)

        return reactions

    def get_new_products(self, reactions):
        """
        Checks the products in the list of reactions. Updates the pointers in
        those reactions to point to pre-existing complexes if necessary. Else,
        returns the new complexes in a list.

        Additionally, prunes passed reactions to remove those with excessively
        large complexes (len(complex) > self.MAX_COMPLEX_SIZE)
        """
        new_products = []
        new_reactions = []

        ESTNF = {c: c for c in self._E + self._S + self._T + self._N + self._F}
        B = {c: c for c in self._B}

        # Loop over every reaction
        for reaction in reactions:

            # This will be set to False if we bail out of the inner loop upon
            # finding a complex that's too large
            complex_size_ok = True

            # Check every product of the reaction to see if it is new
            for (i, product) in enumerate(reaction.products):

                if (len(product.strands) > self.MAX_COMPLEX_SIZE):
                    logging.warning(
                        "Complex %(name)s (%(strands)d strands) too large, ignoring!" % {
                            "name": product.name,
                            "strands": len(
                                product.strands)})
                    complex_size_ok = False
                    break

                # This will be set to True if we've already seen this complex
                enumerated = False

                # If the product is in any of these lists, we don't need to
                # deal with it, so just update the reaction to point correctly
                # TODO: This could benefit from a substantial speedup if _E, _S,
                #	_T, _N, _F were implemented as sets. Other parts of the
                # algorithm benefit from their representation as queues
                # though...

                if product in ESTNF:
                    reaction.products[i] = ESTNF[product]
                    enumerated = True
                # for complex in self._E + self._S + self._T + self._N + self._F:
                # 	if (product == complex):
                # 		enumerated = True
                # 		reaction.products[i] = complex
                # 		break

                if not enumerated:
                    # If the product is in list B, then we need to remove it from
                    # that list so that it can be enumerated for self-interactions
                    # as part of this neighborhood

                    if product in B:
                        reaction.products[i] = B[product]
                        self._B.remove(B[product])
                        product = B[product]
                        del B[product]

                    # for complex in self._B:
                    # 	if (product == complex):
                    # 		reaction.products[i] = complex
                    # 		self._B.remove(complex)
                    # 		product = complex
                    # 		break

                    # If the product has already been seen in this loop, update
                    # the pointer appropriately
                    for complex in new_products:
                        if (product == complex):
                            enumerated = True
                            reaction.products[i] = complex
                            break

                if not enumerated:
                    new_products.append(product)

            # If this reaction contained a complex that was too big, ignore the
            # whole reaction.
            if complex_size_ok:
                new_reactions.append(reaction)

        # Clobber the old value of reactions with the filtered list
        reactions[:] = new_reactions

        assert (set(ESTNF.values()) - set(new_products)) == set(ESTNF.values())
        assert (set(ESTNF.values()) - set(B.values())) == set(ESTNF.values())

        return new_products

    def segment_neighborhood(self, complexes, reactions):
        """
        Segments a set of complexes and reactions between them representing a
        neighborhood into resting states and transient states. Returns the set
        of complexes which are transient states, complexes which are in resting
        states, and the set of resting states, all in a dictionary.

        :param complexes: set of complexes
        :param reactions: set of reactions
        :returns: dictionary with keys:

                *	``resting_states``: set of resting states
                *	``resting_state_complexes``: set of resting state complexes
                *	``transient_state_complexes``: set of transient complexes

        """

        # First we initialize the graph variables that will be used for
        # Tarjan's algorithm

        self._tarjan_index = 0
        self._tarjan_stack = []
        self._SCC_stack = []

        # Set up for Tarjan's algorithm
        for node in complexes:
            node._outward_edges = []
            node._full_outward_edges = []
            node._index = -1
        for reaction in reactions:
            for product in reaction.products:
                product._outward_edges = []
                product._full_outward_edges = []
                product._index = -1

        # Detect which products are actually in the neighborhood
        for reaction in reactions:
            for product in reaction.products:
                product_in_N = False

                for complex in complexes:
                    if (complex == product):
                        product_in_N = True
                        break

                # If this product is in the neighborhood, we have an edge
                if product_in_N:
                    # We know all these reactions are unimolecular
                    reaction.reactants[0]._outward_edges.append(product)
                reaction.reactants[0]._full_outward_edges += (
                    reaction.products)

            node._lowlink = -1

        # We now perform Tarjan's algorithm, marking nodes as appropriate
        for node in complexes:
            if node._index == -1:
                self.tarjans(node)

        # Now check to see which of the SCCs are resting states
        resting_states = []
        resting_state_complexes = []
        transient_state_complexes = []
        for scc in self._SCC_stack:
            scc_products = []
            is_resting_state = True

            for node in scc:
                for product in node._full_outward_edges:
                    scc_products.append(product)

            for product in scc_products:
                product_in_scc = False
                for complex in scc:
                    if product == complex:
                        product_in_scc = True
                        break

                # If the product is not in the SCC, then there is a fast edge
                # leading out of the SCC, so this is not a resting state
                if not product_in_scc:
                    is_resting_state = False
                    break

            if is_resting_state:
                resting_state_complexes += (scc)
                resting_state = utils.RestingState(self.get_auto_name(), scc[:])
                resting_states.append(resting_state)

            else:
                transient_state_complexes += (scc)
        resting_states.sort()
        resting_state_complexes.sort()
        transient_state_complexes.sort()
        return {
            'resting_states': resting_states,
            'resting_state_complexes': resting_state_complexes,
            'transient_state_complexes': transient_state_complexes
        }

    def tarjans(self, node):
        """
        Executes an iteration of Tarjan's algorithm (a modified DFS) starting
        at the given node.
        """
        # Set this node's tarjan numbers
        node._index = self._tarjan_index
        node._lowlink = self._tarjan_index
        self._tarjan_index += 1
        self._tarjan_stack.append(node)
        node._onStack = True

        # Process all connected nodes, setting lowlink as needed
        for next in node._outward_edges:
            if next._index == -1:
                self.tarjans(next)
                node._lowlink = min(node._lowlink, next._lowlink)
            else:
                if next._onStack:
                    node._lowlink = min(node._lowlink, next._lowlink)

        # This indicates that this node is a 'root' node, and children are
        # part of an SCC
        if node._lowlink == node._index:
            stop_flag = False
            scc = []
            while stop_flag == False:
                nextNode = self._tarjan_stack.pop()
                nextNode._onStack = False
                scc.append(nextNode)
                if nextNode == node:
                    stop_flag = True

            # Add the SCC to the list of SCCs
            self._SCC_stack.append(scc)



