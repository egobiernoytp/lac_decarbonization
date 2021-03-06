===========================================
Agriculture, Forestry, and Land Use (AFOLU)
===========================================

INTRO HERE

See the `AFOLU Mathematical Documentation <./mathdoc_afolu.htm>`_ for more information on the model structure, including mathematical formulae and assumptions.


Agriculture
===========

The **Agriculture** subsector is used to quantify emissions associated with growing crops, including emissions from the release of soil carbon, fertilizer applications and crop liming, crop burning, methane emissions from paddy rice fields, **AND MORE;CONTINUE**. Agriculture is divided into the following categories (crops), given by the metavariable ``$CAT-AGRICULTURE$``. Each crop should be associated an FAO classifications. `See the FAO <https://www.fao.org/waicent/faoinfo/economic/faodef/annexe.htm>`_ for the source of these classifications and a complete mapping of crop types to categories. On the git, the table ``ingestion/FAOSTAT/ref/attribute_fao_crop.csv`` contains the information mapping each crop to this crop type. Note, this table can be used to merge and aggregate data from FAO into these categories. If a crop type is not present in a country, set the associated area as a fraction of crop area to 0.

.. note:: Carbon stocks are scaled by 44/12 to estimate :math:`\text{CO}_2` emissions. See Section 2.2.3 of the `IPCC Guidelines for National Greenhouse Gas Inventories <https://www.ipcc.ch/report/2019-refinement-to-the-2006-ipcc-guidelines-for-national-greenhouse-gas-inventories/>`_.

Variables by Category
---------------------

Agriculture requires the following variables.

.. csv-table:: For each agricultural category, trajectories of the following variables are needed.
   :file: ./csvs/table_varreqs_by_category_af_agrc.csv
   :header-rows: 1
.. :widths: 20, 30, 30, 10, 10

.. note::  | To reduce the number of potential variables, types are associated with some key physical characteristics that are used to estimate :math:`\text{N}_2\text{O}` emissions, including :math:`\text{N}_{AG(T)}`, :math:`\text{N}_{BG(T)}`, :math:`\text{R}_{AG(T)}`, :math:`\text{RS}_{T}`, and :math:`DRY`, which are derived from Table 11.1 in Volume 4, Chapter 11 of the `IPCC Guidelines for National Greenhouse Gas Inventories <https://www.ipcc-nggip.iges.or.jp/public/2019rf/pdf/4_Volume4/19R_V4_Ch11_Soils_N2O_CO2.pdf>`_.
 |
 | These variables are used in Equations 11.6 and 11.7 (Volume 4) of the IPCC NGHGI to estimate :math:`\text{N}_2\text{O}`

Categories
----------

Agriculture is divided into the following categories.

.. csv-table:: Agricultural categories (``$CAT-AGRICULTURE$`` attribute table)
   :file: ./csvs/attribute_cat_agriculture.csv
   :header-rows: 1
..   :widths: 15,15,30,15,10,15



**Costs to be added**

----

Forestry
========

Variables by Category
---------------------

.. csv-table:: For each forest category, trajectories of the following variables are needed.
   :file: ./csvs/table_varreqs_by_category_af_frst.csv
   :header-rows: 1

Variables by Partial Category
-----------------------------

Forestry includes some variables that apply only to a subset of categories. These variables are described below. The categories that variables apply to are described in the ``category`` column.

.. csv-table:: Trajectories of the following variables are needed for **some** forest categories. If they are independent of categories, the category will show up as **none**.
   :file: ./csvs/table_varreqs_by_partial_category_af_frst.csv
   :header-rows: 1

Categories
----------

Forestry is divided into the following categories. These categories reflect an aggregation of forestry types into emission-relevant categories. Note that areas of forested land are determined in the **Land Use** subsector. The land use at time *t* is determined by an ergodic Markov Chain (probabilities are set in the variable input table and subject to uncertainty using the mixing approach)

.. csv-table:: Forest categories (``$CAT-FOREST$`` attribute table)
   :file: ./csvs/attribute_cat_forest.csv
   :header-rows: 1
..   :widths: 15,15,30,15,10,15


----

Land Use
========

Land use projections are driven by a Markov Chain, represented by a transition matrix :math:`Q(t)` (the matrix is specified for each time period in the ``model_input_variables.csv`` file). The model requires initial states (entered as a fraction of total land area) for all land use categories ``$CAT-LANDUSE$``. See the `AFOLU Mathematical Documentation <./mathdoc_afolu.htm>`_ for more information on the integrated land use model.

.. note::
   The entries :math:`Q_{ij}(t)` give the transition probability of land use category :math:`i` to land use category :math:`j`. :math:`Q` is row stochastic, so that :math:`\sum_{j}Q_{ij}(t) = 1` for each land use category :math:`i` and time period :math:`t`. To preserve row stochasticity, it is highly recommended that strategies and uncertainty be represented using the trajectory mixing approach, where bounding trajectories on transitions probabilities are specified and uncertainty exploration gives a mix between them.


Variables by Category
---------------------

.. csv-table:: For each land use category, trajectories of the following variables are needed.
   :file: ./csvs/table_varreqs_by_category_af_lndu.csv
   :header-rows: 1

Variables by Partial Category
-----------------------------

Land use includes some variables that apply only to a subset of categories. These variables are described below. The categories that variables apply to are described in the ``category`` column.

.. note::
   Note that the sum of all initial fractions of area across land use categories *u* should be should equal 1to , i.e. :math:`\sum_u \varphi_u = 1`, where :math:`\varphi_{\text{$CAT-LANDUSE$}} \to` ``frac_lu_$CAT-LANDUSE$`` at period *t*.

.. csv-table:: Trajectories of the following variables are needed for **some** land use categories.
   :file: ./csvs/table_varreqs_by_partial_category_af_lndu.csv
   :header-rows: 1
.. :widths: 15, 15, 20, 10, 10, 10, 10, 10

Categories
----------

Land use should be divided into the following categories, given by ``$CAT-LANDUSE$``.

.. csv-table:: Land Use categories (``$CAT-LANDUSE$`` attribute table)
   :file: ./csvs/attribute_cat_land_use.csv
   :header-rows: 1

----


Livestock
=========

For each category, the following variables are needed. Information on enteric fermentation can be found from `the EPA <https://www3.epa.gov/ttnchie1/ap42/ch14/final/c14s04.pdf>`_ and **ADDITIONAL LINKS HERE**.

Variables by Category
---------------------

.. csv-table:: For each livestock category, trajectories of the following variables are needed.
   :file: ./csvs/table_varreqs_by_category_af_lvst.csv
   :header-rows: 1

Variables by Partial Category
-----------------------------

Livestock includes some variables that apply only to a subset of categories. These variables are described below. The categories that variables apply to are described in the ``category`` column.

.. csv-table:: Trajectories of the following variables are needed for **some** livestock categories.
   :file: ./csvs/table_varreqs_by_partial_category_af_lvst.csv
   :header-rows: 1

Categories
----------

Livestock should be divided into the following categories, given by ``$CAT-LIVESTOCK$``.

.. note::
   Animal weights are only used to estimate the increase in protein consumption in liquid waste (which contribute to :math:`\text{N}_2\text{O}` emissions). All estimates are adapted from `Holechek 1988 <https://journals.uair.arizona.edu/index.php/rangelands/article/download/10362/9633>`_ (using 2.2 lbs/kg) unless otherwise noted.

.. csv-table:: Livestock categories (``$CAT-LIVESTOCK$`` attribute table)
   :file: ./csvs/attribute_cat_livestock.csv
   :header-rows: 1



Livestock Manure Management
===========================

EXPLANATION HERE

Variables by Category
---------------------

.. csv-table:: For each livestock category, trajectories of the following variables are needed.
   :file: ./csvs/table_varreqs_by_category_af_lsmm.csv
   :header-rows: 1


Variables by Partial Category
-----------------------------

Livestock manure management includes some variables that apply only to a subset of categories. These variables are described below. The categories that variables apply to are described in the ``category`` column.

   .. csv-table:: Trajectories of the following variables are needed for **some** livestock manure management categories.
      :file: ./csvs/table_varreqs_by_partial_category_af_lsmm.csv
      :header-rows: 1


Categories
----------

Manure management is divided into the following categories, given by ``$CAT-MANURE-MANAGEMENT$``.

.. csv-table:: Livestock manure management categories (``$CAT-MANURE-MANAGEMENT$`` attribute table)
   :file: ./csvs/attribute_cat_manure_management.csv
   :header-rows: 1



Soil Management
===============

EXPLANATION HERE

Variables by Category
---------------------

.. csv-table:: For each soil management category, trajectories of the following variables are needed.
   :file: ./csvs/table_varreqs_by_category_af_soil.csv
   :header-rows: 1


Variables by Partial Category
-----------------------------

   Soil management includes some variables that apply only to a subset of categories. These variables are described below. The categories that variables apply to are described in the ``category`` column.

   .. csv-table:: Trajectories of the following variables are needed for **some** soil management categories.
      :file: ./csvs/table_varreqs_by_partial_category_af_soil.csv
      :header-rows: 1


Categories
----------

Soil management is divided into the following categories, given by ``$CAT-SOIL-MANAGEMENT$``.

.. csv-table:: Soil management categories (``$CAT-SOIL-MANAGEMENT$`` attribute table)
   :file: ./csvs/attribute_cat_soil_management.csv
   :header-rows: 1
