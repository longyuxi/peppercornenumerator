# peppercornenumerator 

This package enumerates domain-level strand displacement (DSD) reaction
networks assuming low species concentrations, such that unimolecular reaction
pathways always equilibrate before bimolecular reactions initiate. The
enumerator can handle arbitrary non-pseudoknotted structures and supports a
diverse set of unimolecular and bimolecular domain-level reactions: bind/unbind
reactions, 3-way branch-migration and 4-way branch-migration reactions and
remote toehold migration. For more background on reaction semantics we refer to
the publication [Grun et al. (2014)].

## Installation
```bash
$ python setup.py install
```
or
```
$ python setup.py install --user
```

## Quickstart using the executable "peppercorn"

### Quickstart
Load the file `system.pil`, write results to `system-enum.pil`:

```sh
$ peppercorn -o system-enum.pil system.pil
```
or read from STDIN and write to STDOUT:

```sh
$ cat system.pil | peppercorn > system-enum.pil
```


### Input/Output format

The following input format is recommended. Sequence-level details may be
provided, however they will be ignored during enumeration and rate computation.

```
# Shohei Kotani and William L. Hughes (2017)
# Multi-Arm Junctions for Dynamic DNA Nanotechnology
# 
# Figure 2A: Single-layer catalytic system with three-arm junction substrates.
length a   = 22
length b   = 22
length c   = 22
length t1  = 6   # name = 1 in Figure 
length t2  = 6   # name = 2 in Figure
length t3  = 10  # name = 3 in Figure
length T2  = 2

length d1s = 16
length d2  = 6

S1 = d1s T2 b( a( t2( + ) ) c*( t1* + ) )
S2 = t1( c( a( + t2* ) b*( d2 t3 + ) ) )
C1 = t1 c a

P1 = t2* a*( c*( t1*( + ) ) )
I1 = d1s T2 b( a t2 + c )
I2 = d1s T2 b( a( t2( + ) ) b*( d2 t3 + ) c*( t1* + ) )

P2 = d1s T2 b( a( t2( + ) ) ) d2 t3
P3 = b( c*( t1* + ) )

R = d1s( d2( + t3* ) )

D = d1s d2
RW = d1s( T2 b( a( t2( + ) ) ) d2( t3( + ) ) )
```

```
$ peppercorn -o system-enum.pil --max-complex-size 10 < system.pil
```

```
# File generated by peppercorn-v0.6

# Domain specifications 
length a = 22
length b = 22
length c = 22
length d1s = 16
length d2 = 6
length t1 = 6
length T2 = 2
length t2 = 6
length t3 = 10

# Resting complexes 
C1 = t1 c a
D = d1s d2
e48 = t3*( d2*( d1s*( + ) ) + b( c*( t1*( + ) ) a( + t2* ) ) d2 )
e51 = t3*( d2*( d1s*( + ) d2 + b( c*( t1*( + ) ) a( + t2* ) ) ) )
I1 = d1s T2 b( a t2 + c )
P1 = t2* a*( c*( t1*( + ) ) )
P2 = d1s T2 b( a( t2( + ) ) ) d2 t3
P3 = b( c*( t1* + ) )
R = d1s( d2( + t3* ) )
RW = d1s( T2 b( a( t2( + ) ) ) d2( t3( + ) ) )
S1 = d1s T2 b( a( t2( + ) ) c*( t1* + ) )
S2 = t1( c( a( + t2* ) b*( d2 t3 + ) ) )

# Resting macrostates 
macrostate C1 = [C1]
macrostate D = [D]
macrostate e51 = [e51, e48]
macrostate I1 = [I1]
macrostate P1 = [P1]
macrostate P2 = [P2]
macrostate P3 = [P3]
macrostate R = [R]
macrostate RW = [RW]
macrostate S1 = [S1]
macrostate S2 = [S2]

# Condensed reactions 
reaction [condensed      =       588645 /M/s ] e51 + I1 -> P3 + RW + D + C1
reaction [condensed      =      3083.77 /M/s ] I1 + P1 -> S1 + C1
reaction [condensed      =        3e+06 /M/s ] P2 + R -> RW + D
reaction [condensed      =    1.637e+06 /M/s ] S1 + C1 -> I1 + P1
reaction [condensed      =       588645 /M/s ] S2 + I1 -> P3 + P2 + C1
reaction [condensed      =        3e+06 /M/s ] S2 + R -> e51
```

## Version
0.6.2

## Authors
Casey Grun, Stefan Badelt, Karthik Sarma, Brian Wolfe, Seung Woo Shin and Erik Winfree.

[Grun et al. (2014)]: <https://arxiv.org/abs/1505.03738>

