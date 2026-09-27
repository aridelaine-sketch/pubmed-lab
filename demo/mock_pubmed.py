"""
This file stands in for app.pubmed.engine.PubMedEngine ONLY because this
sandbox's network policy blocks eutils.ncbi.nlm.nih.gov (verified: a
direct request returns HTTP 403 / "Host not in allowlist"). On a real
machine, PubMedEngine hits the live API exactly as implemented in
app/pubmed/eutils.py and app/pubmed/pmc_oa.py -- nothing else in this
demo is mocked.

The abstracts below are short, realistic paraphrases (not verbatim
quotes) written to exercise supporting / contradicting / qualifying
classification, attached to real-looking but placeholder PMIDs.
"""

from __future__ import annotations

from app.pubmed.models import Paper


def fixture_papers_for(term: str) -> list[Paper]:
    term_l = term.lower()

    if "eisenmenger" in term_l or "hemoptysis" in term_l:
        return [
            Paper(
                pmid="20000001", title="Pulmonary vascular remodeling in Eisenmenger syndrome",
                journal="J Pulm Vasc Res", year="2019", authors=["Alvarez R", "Kim S"], doi="10.9999/jpvr.2019.001",
                abstract=(
                    "Eisenmenger syndrome results from long-standing left-to-right shunting that "
                    "reverses into a right-to-left shunt once pulmonary vascular resistance exceeds "
                    "systemic resistance. Chronic hypoxemia drives compensatory erythrocytosis and "
                    "fragile bronchial collateral vessel formation. Rupture of these dilated, "
                    "thin-walled collaterals is considered the primary mechanism of hemoptysis in "
                    "this population. In a retrospective cohort, hemoptysis occurred in roughly 20% "
                    "of adult patients with Eisenmenger syndrome followed over a decade."
                ),
            ),
            Paper(
                pmid="20000002", title="Coagulopathy and bleeding risk in cyanotic congenital heart disease",
                journal="Cardiol Rev", year="2021", authors=["Nasser F"], doi="10.9999/cr.2021.014",
                abstract=(
                    "Patients with cyanotic congenital heart disease frequently develop secondary "
                    "erythrocytosis, thrombocytopenia, and acquired coagulation factor abnormalities. "
                    "These hematologic changes compound the vascular fragility from bronchial "
                    "collateral hypertrophy, so hemoptysis in Eisenmenger syndrome is usually "
                    "multifactorial rather than attributable to vessel rupture alone."
                ),
            ),
        ]

    if "copd" in term_l:
        return [
            Paper(
                pmid="20000010", title="Prevalence of pulmonary hypertension across GOLD stages of COPD",
                journal="Respir Med", year="2020", authors=["Bianchi L", "Tran H"], doi="10.9999/rm.2020.220",
                abstract=(
                    "Mild pulmonary hypertension is common in COPD and is largely explained by "
                    "hypoxic pulmonary vasoconstriction and vascular remodeling. In a multicenter "
                    "cohort, mean pulmonary artery pressure correlated with the severity of airflow "
                    "obstruction, supporting an association between COPD and pulmonary hypertension."
                ),
            ),
            Paper(
                pmid="20000011", title="Severe pulmonary hypertension out of proportion to COPD severity",
                journal="Eur Respir J", year="2022", authors=["Okafor C"], doi="10.9999/erj.2022.077",
                abstract=(
                    "A subset of COPD patients develop pulmonary hypertension that is disproportionately "
                    "severe relative to their airflow limitation. In this subgroup, right heart "
                    "catheterization is recommended and alternative or additional causes of pulmonary "
                    "hypertension should be actively excluded before attributing it to COPD alone."
                ),
            ),
        ]

    # generic pulmonary hypertension learning-mode fixtures, keyed loosely by section keyword
    generic = {
        "definition": Paper(
            pmid="20000100", title="Hemodynamic definition of pulmonary hypertension: 2022 update",
            journal="Eur Heart J", year="2022", authors=["Delcroix M"], doi="10.9999/ehj.2022.301",
            abstract=(
                "Pulmonary hypertension is now defined hemodynamically as a mean pulmonary arterial "
                "pressure greater than 20 mmHg at rest, measured by right heart catheterization, "
                "revised downward from the prior 25 mmHg threshold."
            ),
        ),
        "classification": Paper(
            pmid="20000101", title="The 2022 clinical classification of pulmonary hypertension",
            journal="Eur Respir J", year="2022", authors=["Simonneau G"], doi="10.9999/erj.2022.056",
            abstract=(
                "Pulmonary hypertension is grouped into five clinical categories: pulmonary arterial "
                "hypertension, pulmonary hypertension due to left heart disease, due to lung disease "
                "or hypoxia, due to pulmonary artery obstructions, and with unclear or multifactorial "
                "mechanisms."
            ),
        ),
        "pathophysiology": Paper(
            pmid="20000102", title="Vascular remodeling mechanisms in pulmonary arterial hypertension",
            journal="Circ Res", year="2021", authors=["Humbert M", "Guignabert C"], doi="10.9999/cr.2021.410",
            abstract=(
                "Sustained endothelial dysfunction, smooth muscle proliferation, and in-situ thrombosis "
                "progressively narrow the pulmonary arterioles, raising pulmonary vascular resistance "
                "and right ventricular afterload."
            ),
        ),
        "epidemiology": Paper(
            pmid="20000103", title="Estimated prevalence of pulmonary arterial hypertension in Europe",
            journal="Eur Respir Rev", year="2020", authors=["Hoeper M"], doi="10.9999/err.2020.045",
            abstract=(
                "Registry-based estimates place the prevalence of pulmonary arterial hypertension at "
                "roughly 15 to 60 cases per million adults, with idiopathic and connective-tissue-disease-"
                "associated forms accounting for most incident cases."
            ),
        ),
        "manifestation": Paper(
            pmid="20000104", title="Presenting symptoms and delayed diagnosis in pulmonary hypertension",
            journal="Chest", year="2019", authors=["Farber H"], doi="10.9999/chest.2019.188",
            abstract=(
                "Exertional dyspnea is the most common presenting symptom of pulmonary hypertension, "
                "often accompanied by fatigue and, in advanced disease, syncope and signs of right "
                "heart failure such as peripheral edema."
            ),
        ),
        "diagnosis": Paper(
            pmid="20000105", title="Diagnostic algorithm for suspected pulmonary hypertension",
            journal="Eur Heart J", year="2022", authors=["Humbert M"], doi="10.9999/ehj.2022.302",
            abstract=(
                "Transthoracic echocardiography is the recommended first-line screening test for "
                "suspected pulmonary hypertension, with right heart catheterization required to "
                "confirm the diagnosis and classify its hemodynamic subtype."
            ),
        ),
        "hemodynamic": Paper(
            pmid="20000106", title="Hemodynamic profiling by right heart catheterization in PH",
            journal="J Am Coll Cardiol", year="2021", authors=["Vachiery J"], doi="10.9999/jacc.2021.099",
            abstract=(
                "Right heart catheterization distinguishes pre-capillary from post-capillary pulmonary "
                "hypertension using pulmonary arterial wedge pressure and pulmonary vascular resistance, "
                "which determines treatment eligibility."
            ),
        ),
        "treatment": Paper(
            pmid="20000107", title="Pulmonary arterial hypertension-targeted therapy: a review",
            journal="Lancet Respir Med", year="2023", authors=["Galie N"], doi="10.9999/lrm.2023.019",
            abstract=(
                "Endothelin receptor antagonists, phosphodiesterase-5 inhibitors, and prostacyclin "
                "pathway agents form the backbone of pulmonary arterial hypertension-targeted therapy, "
                "with combination therapy now favored over sequential monotherapy in most patients."
            ),
        ),
        "prognosis": Paper(
            pmid="20000108", title="Long-term survival trends in pulmonary arterial hypertension",
            journal="Eur Respir J", year="2021", authors=["Benza R"], doi="10.9999/erj.2021.140",
            abstract=(
                "Contemporary registries report three-year survival above 75% in pulmonary arterial "
                "hypertension, a marked improvement over historical cohorts, attributed largely to "
                "earlier diagnosis and combination targeted therapy."
            ),
        ),
    }
    for key, paper in generic.items():
        if key in term_l:
            return [paper]
    return [generic["definition"]]


class MockPubMedEngine:
    """Same interface as app.pubmed.engine.PubMedEngine.search / close."""

    def search(self, term: str, retmax: int = 10) -> list[Paper]:
        return fixture_papers_for(term)[:retmax]

    def close(self) -> None:
        pass
