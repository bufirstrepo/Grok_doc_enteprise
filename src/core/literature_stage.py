"""
Literature Synthesis Stage for Grok Doc v2.5

Integrates with PubMed/NCBI to:
1. Build optimized search queries from clinical questions
2. Retrieve relevant abstracts via E-utilities API
3. Synthesize and summarize evidence
4. Grade evidence levels (I-V hierarchy)
5. Return structured literature support for recommendations
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import json
import time
import re
import urllib.parse


class EvidenceLevel(Enum):
    """Evidence grading hierarchy based on study design"""
    LEVEL_I = "Level I"      # Systematic reviews, meta-analyses of RCTs
    LEVEL_II = "Level II"    # Randomized controlled trials
    LEVEL_III = "Level III"  # Controlled trials without randomization
    LEVEL_IV = "Level IV"    # Case-control, cohort studies
    LEVEL_V = "Level V"      # Case reports, expert opinion
    UNKNOWN = "Unknown"
    
    @classmethod
    def from_publication_type(cls, pub_types: List[str]) -> "EvidenceLevel":
        """Determine evidence level from PubMed publication types"""
        pub_types_lower = [pt.lower() for pt in pub_types]
        
        level_i_markers = [
            'meta-analysis', 'systematic review', 'systematic reviews',
            'practice guideline', 'guideline', 'cochrane database'
        ]
        if any(marker in ' '.join(pub_types_lower) for marker in level_i_markers):
            return cls.LEVEL_I
        
        level_ii_markers = [
            'randomized controlled trial', 'randomized', 'rct',
            'controlled clinical trial', 'multicenter study'
        ]
        if any(marker in ' '.join(pub_types_lower) for marker in level_ii_markers):
            return cls.LEVEL_II
        
        level_iii_markers = [
            'clinical trial', 'controlled study', 'comparative study',
            'evaluation study', 'validation study'
        ]
        if any(marker in ' '.join(pub_types_lower) for marker in level_iii_markers):
            return cls.LEVEL_III
        
        level_iv_markers = [
            'cohort', 'case-control', 'observational study',
            'longitudinal study', 'retrospective', 'prospective'
        ]
        if any(marker in ' '.join(pub_types_lower) for marker in level_iv_markers):
            return cls.LEVEL_IV
        
        level_v_markers = [
            'case report', 'case series', 'letter', 'comment',
            'editorial', 'review', 'expert opinion'
        ]
        if any(marker in ' '.join(pub_types_lower) for marker in level_v_markers):
            return cls.LEVEL_V
        
        return cls.UNKNOWN


@dataclass
class Citation:
    """Structured citation from PubMed"""
    pmid: str
    title: str
    authors: List[str]
    journal: str
    year: str
    abstract: str
    publication_types: List[str]
    evidence_level: EvidenceLevel
    mesh_terms: List[str] = field(default_factory=list)
    doi: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'pmid': self.pmid,
            'title': self.title,
            'authors': self.authors,
            'journal': self.journal,
            'year': self.year,
            'abstract': self.abstract[:500] + '...' if len(self.abstract) > 500 else self.abstract,
            'publication_types': self.publication_types,
            'evidence_level': self.evidence_level.value,
            'mesh_terms': self.mesh_terms,
            'doi': self.doi
        }
    
    def format_ama(self) -> str:
        """Format citation in AMA style"""
        author_str = ', '.join(self.authors[:3])
        if len(self.authors) > 3:
            author_str += ', et al'
        return f"{author_str}. {self.title}. {self.journal}. {self.year}."
    
    def format_short(self) -> str:
        """Format short citation"""
        first_author = self.authors[0].split()[-1] if self.authors else "Unknown"
        return f"{first_author} et al. ({self.year}) - {self.evidence_level.value}"


@dataclass
class LiteratureInput:
    """Input for literature synthesis"""
    clinical_question: str
    patient_context: Dict[str, Any]
    primary_recommendation: Optional[str] = None
    max_results: int = 10
    min_evidence_level: EvidenceLevel = EvidenceLevel.LEVEL_V
    metadata: Optional[Dict] = None


@dataclass
class LiteratureResult:
    """Result from literature synthesis"""
    clinical_question: str
    search_query: str
    citations: List[Citation]
    evidence_summary: str
    highest_evidence_level: EvidenceLevel
    evidence_distribution: Dict[str, int]
    supports_recommendation: bool
    confidence_score: float
    synthesis_notes: str
    timestamp: str
    hash: str
    pubmed_available: bool
    model_used: Optional[str] = None
    latency_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'clinical_question': self.clinical_question,
            'search_query': self.search_query,
            'citations': [c.to_dict() for c in self.citations],
            'citation_count': len(self.citations),
            'evidence_summary': self.evidence_summary,
            'highest_evidence_level': self.highest_evidence_level.value,
            'evidence_distribution': self.evidence_distribution,
            'supports_recommendation': self.supports_recommendation,
            'confidence_score': self.confidence_score,
            'synthesis_notes': self.synthesis_notes,
            'timestamp': self.timestamp,
            'hash': self.hash,
            'pubmed_available': self.pubmed_available,
            'model_used': self.model_used,
            'latency_ms': self.latency_ms
        }


class PubMedClient:
    """
    Client for NCBI PubMed E-utilities API.
    
    Uses the public API which allows limited requests without an API key.
    For higher rate limits, set NCBI_API_KEY environment variable.
    
    API Documentation: https://www.ncbi.nlm.nih.gov/books/NBK25500/
    """
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        email: Optional[str] = None,
        tool_name: str = "GrokDoc"
    ):
        """
        Initialize PubMed client.
        
        Args:
            api_key: NCBI API key (optional, increases rate limit)
            email: Contact email for NCBI (recommended)
            tool_name: Tool identifier for NCBI
        """
        import os
        self.api_key = api_key or os.getenv('NCBI_API_KEY')
        self.email = email or os.getenv('NCBI_EMAIL', 'grokdoc@example.com')
        self.tool_name = tool_name
        self._session = None
    
    def _get_session(self):
        """Get or create HTTP session"""
        if self._session is None:
            try:
                import requests
                self._session = requests.Session()
                self._session.headers.update({
                    'User-Agent': f'{self.tool_name}/1.0'
                })
            except ImportError:
                raise RuntimeError("requests library required for PubMed API")
        return self._session
    
    def _build_params(self, **kwargs) -> Dict[str, str]:
        """Build API parameters with authentication"""
        params = {
            'tool': self.tool_name,
            'email': self.email,
            'retmode': 'json'
        }
        if self.api_key:
            params['api_key'] = self.api_key
        params.update({k: v for k, v in kwargs.items() if v is not None})
        return params
    
    def search(
        self,
        query: str,
        max_results: int = 10,
        sort: str = "relevance",
        min_date: Optional[str] = None,
        max_date: Optional[str] = None
    ) -> List[str]:
        """
        Search PubMed and return list of PMIDs.
        
        Args:
            query: PubMed search query
            max_results: Maximum number of results
            sort: Sort order (relevance, pub_date)
            min_date: Minimum publication date (YYYY/MM/DD)
            max_date: Maximum publication date (YYYY/MM/DD)
            
        Returns:
            List of PMIDs
        """
        try:
            session = self._get_session()
            
            params = self._build_params(
                db='pubmed',
                term=query,
                retmax=str(max_results),
                sort=sort,
                mindate=min_date,
                maxdate=max_date
            )
            
            response = session.get(
                f"{self.BASE_URL}/esearch.fcgi",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            result = data.get('esearchresult', {})
            
            if 'ERROR' in data or 'error' in result:
                raise RuntimeError(f"PubMed search error: {data.get('ERROR') or result.get('error')}")
            
            return result.get('idlist', [])
            
        except Exception as e:
            raise RuntimeError(f"PubMed search failed: {e}")
    
    def fetch_details(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch article details for given PMIDs.
        
        Args:
            pmids: List of PubMed IDs
            
        Returns:
            List of article detail dictionaries
        """
        if not pmids:
            return []
        
        try:
            session = self._get_session()
            
            params = self._build_params(
                db='pubmed',
                id=','.join(pmids),
                rettype='abstract'
            )
            
            response = session.get(
                f"{self.BASE_URL}/efetch.fcgi",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            params_summary = self._build_params(
                db='pubmed',
                id=','.join(pmids),
                retmode='json'
            )
            
            response_summary = session.get(
                f"{self.BASE_URL}/esummary.fcgi",
                params=params_summary,
                timeout=30
            )
            response_summary.raise_for_status()
            
            summary_data = response_summary.json()
            result = summary_data.get('result', {})
            
            articles = []
            for pmid in pmids:
                if pmid in result and pmid != 'uids':
                    article = result[pmid]
                    articles.append({
                        'pmid': pmid,
                        'title': article.get('title', ''),
                        'authors': [
                            auth.get('name', '') 
                            for auth in article.get('authors', [])
                        ],
                        'journal': article.get('fulljournalname', article.get('source', '')),
                        'year': article.get('pubdate', '')[:4],
                        'publication_types': article.get('pubtype', []),
                        'doi': self._extract_doi(article.get('elocationid', '')),
                        'abstract': article.get('abstract', ''),
                    })
            
            return articles
            
        except Exception as e:
            raise RuntimeError(f"PubMed fetch failed: {e}")
    
    def fetch_abstracts(self, pmids: List[str]) -> Dict[str, str]:
        """
        Fetch abstracts for given PMIDs using efetch with XML parsing.
        
        Args:
            pmids: List of PubMed IDs
            
        Returns:
            Dict mapping PMID to abstract text
        """
        if not pmids:
            return {}
        
        try:
            session = self._get_session()
            
            params = {
                'db': 'pubmed',
                'id': ','.join(pmids),
                'rettype': 'abstract',
                'retmode': 'xml',
                'tool': self.tool_name,
                'email': self.email
            }
            if self.api_key:
                params['api_key'] = self.api_key
            
            response = session.get(
                f"{self.BASE_URL}/efetch.fcgi",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            abstracts = {}
            xml_content = response.text
            
            abstract_pattern = re.compile(
                r'<PMID[^>]*>(\d+)</PMID>.*?<AbstractText[^>]*>(.*?)</AbstractText>',
                re.DOTALL
            )
            
            for match in re.finditer(r'<PubmedArticle>(.*?)</PubmedArticle>', xml_content, re.DOTALL):
                article_xml = match.group(1)
                
                pmid_match = re.search(r'<PMID[^>]*>(\d+)</PMID>', article_xml)
                if pmid_match:
                    pmid = pmid_match.group(1)
                    
                    abstract_texts = re.findall(r'<AbstractText[^>]*>(.*?)</AbstractText>', article_xml, re.DOTALL)
                    if abstract_texts:
                        abstract = ' '.join(abstract_texts)
                        abstract = re.sub(r'<[^>]+>', '', abstract)
                        abstracts[pmid] = abstract.strip()
            
            return abstracts
            
        except Exception as e:
            return {}
    
    def _extract_doi(self, elocation_id: str) -> Optional[str]:
        """Extract DOI from elocation ID"""
        if 'doi:' in elocation_id.lower():
            return elocation_id.replace('doi:', '').strip()
        return None
    
    def is_available(self) -> bool:
        """Check if PubMed API is accessible"""
        try:
            session = self._get_session()
            response = session.get(
                f"{self.BASE_URL}/einfo.fcgi",
                params={'db': 'pubmed', 'retmode': 'json'},
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False


class LiteratureStage:
    """
    Literature synthesis stage that retrieves and synthesizes
    PubMed evidence for clinical recommendations.
    
    This stage:
    1. Builds optimized PubMed search queries from clinical questions
    2. Retrieves relevant abstracts
    3. Grades evidence levels (I-V)
    4. Synthesizes findings with LLM
    5. Returns structured literature support
    """
    
    CLINICAL_SEARCH_FILTERS = {
        'therapy': '[Therapy/Broad[filter]]',
        'diagnosis': '[Diagnosis[filter]]',
        'prognosis': '[Prognosis[filter]]',
        'etiology': '[Etiology[filter]]',
        'systematic_review': 'systematic[sb]',
        'rct': 'randomized controlled trial[pt]',
        'meta_analysis': 'meta-analysis[pt]',
        'human': 'humans[mh]',
        'english': 'english[la]'
    }
    
    def __init__(
        self,
        use_llm: bool = True,
        model_name: Optional[str] = None,
        max_results: int = 10,
        prefer_high_evidence: bool = True,
        pubmed_client: Optional[PubMedClient] = None
    ):
        """
        Initialize Literature Stage.
        
        Args:
            use_llm: Whether to use LLM for synthesis
            model_name: Specific model to use
            max_results: Maximum citations to retrieve
            prefer_high_evidence: Prioritize systematic reviews/RCTs
            pubmed_client: Optional pre-configured PubMed client
        """
        self.use_llm = use_llm
        self.model_name = model_name
        self.max_results = max_results
        self.prefer_high_evidence = prefer_high_evidence
        self.pubmed_client = pubmed_client or PubMedClient()
    
    def analyze(self, input_data: LiteratureInput) -> LiteratureResult:
        """
        Perform literature synthesis for a clinical question.
        
        Args:
            input_data: LiteratureInput with question and context
            
        Returns:
            LiteratureResult with evidence synthesis
        """
        start_time = time.time()
        
        search_query = self._build_search_query(
            input_data.clinical_question,
            input_data.patient_context
        )
        
        pubmed_available = self.pubmed_client.is_available()
        
        if pubmed_available:
            try:
                citations = self._retrieve_citations(
                    search_query,
                    input_data.max_results or self.max_results
                )
            except Exception as e:
                citations = []
                pubmed_available = False
        else:
            citations = []
        
        if not citations:
            return self._generate_fallback_result(
                input_data,
                search_query,
                pubmed_available,
                time.time() - start_time
            )
        
        if self.use_llm:
            try:
                synthesis = self._synthesize_with_llm(citations, input_data)
            except Exception:
                synthesis = self._synthesize_fallback(citations, input_data)
        else:
            synthesis = self._synthesize_fallback(citations, input_data)
        
        evidence_dist = self._calculate_evidence_distribution(citations)
        highest_level = self._get_highest_evidence_level(citations)
        confidence = self._calculate_confidence(citations, highest_level)
        
        supports = self._assess_recommendation_support(
            citations,
            input_data.primary_recommendation
        )
        
        result_hash = self._compute_hash(input_data, synthesis)
        
        return LiteratureResult(
            clinical_question=input_data.clinical_question,
            search_query=search_query,
            citations=citations,
            evidence_summary=synthesis['summary'],
            highest_evidence_level=highest_level,
            evidence_distribution=evidence_dist,
            supports_recommendation=supports,
            confidence_score=confidence,
            synthesis_notes=synthesis['notes'],
            timestamp=datetime.utcnow().isoformat() + "Z",
            hash=result_hash,
            pubmed_available=pubmed_available,
            model_used=self.model_name or "default",
            latency_ms=(time.time() - start_time) * 1000
        )
    
    def _build_search_query(
        self,
        clinical_question: str,
        patient_context: Dict[str, Any]
    ) -> str:
        """
        Build an optimized PubMed search query.
        
        Uses clinical question keywords and patient context
        to construct a targeted search.
        """
        keywords = self._extract_clinical_keywords(clinical_question)
        
        query_parts = []
        
        if keywords:
            main_terms = ' AND '.join([f'"{kw}"' if ' ' in kw else kw for kw in keywords[:5]])
            query_parts.append(f"({main_terms})")
        
        age = patient_context.get('age')
        if age is not None:
            if age < 18:
                query_parts.append('(pediatric[tiab] OR child[tiab] OR adolescent[tiab])')
            elif age >= 65:
                query_parts.append('(elderly[tiab] OR geriatric[tiab] OR aged[mh])')
        
        conditions = patient_context.get('conditions', []) or patient_context.get('diagnoses', [])
        if conditions and isinstance(conditions, list):
            cond_str = conditions[0] if conditions else None
            if cond_str and isinstance(cond_str, str):
                clean_cond = cond_str.split()[0] if ' ' in cond_str else cond_str
                if len(clean_cond) > 3:
                    query_parts.append(f'("{clean_cond}"[tiab])')
        
        if self.prefer_high_evidence:
            query_parts.append('(systematic[sb] OR randomized controlled trial[pt])')
        
        query_parts.append(self.CLINICAL_SEARCH_FILTERS['human'])
        query_parts.append(self.CLINICAL_SEARCH_FILTERS['english'])
        
        final_query = ' AND '.join(query_parts)
        
        return final_query
    
    def _extract_clinical_keywords(self, question: str) -> List[str]:
        """Extract clinically relevant keywords from question"""
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'shall',
            'can', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
            'from', 'as', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'between', 'under', 'again', 'further',
            'then', 'once', 'here', 'there', 'when', 'where', 'why',
            'how', 'all', 'each', 'few', 'more', 'most', 'other', 'some',
            'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
            'than', 'too', 'very', 'just', 'what', 'which', 'who', 'this',
            'that', 'these', 'those', 'i', 'me', 'my', 'we', 'our', 'you',
            'your', 'he', 'him', 'his', 'she', 'her', 'it', 'its', 'they',
            'them', 'their', 'patient', 'patients', 'treatment', 'use',
            'using', 'best', 'recommend', 'recommendation', 'clinical'
        }
        
        text = question.lower()
        text = re.sub(r'[^\w\s-]', ' ', text)
        words = text.split()
        
        keywords = []
        for word in words:
            if word not in stop_words and len(word) > 2:
                keywords.append(word)
        
        multi_word_patterns = [
            r'\b(heart failure)\b',
            r'\b(blood pressure)\b',
            r'\b(type \d diabetes)\b',
            r'\b(coronary artery disease)\b',
            r'\b(atrial fibrillation)\b',
            r'\b(chronic kidney disease)\b',
            r'\b(deep vein thrombosis)\b',
            r'\b(pulmonary embolism)\b',
        ]
        
        for pattern in multi_word_patterns:
            match = re.search(pattern, question.lower())
            if match:
                keywords.insert(0, match.group(1))
        
        return keywords[:8]
    
    def _retrieve_citations(self, query: str, max_results: int) -> List[Citation]:
        """Retrieve and parse citations from PubMed"""
        pmids = self.pubmed_client.search(
            query,
            max_results=max_results,
            sort="relevance"
        )
        
        if not pmids:
            simplified_query = query.split(' AND ')[0]
            pmids = self.pubmed_client.search(
                simplified_query,
                max_results=max_results
            )
        
        if not pmids:
            return []
        
        articles = self.pubmed_client.fetch_details(pmids)
        
        abstracts = self.pubmed_client.fetch_abstracts(pmids)
        
        citations = []
        for article in articles:
            pmid = article.get('pmid', '')
            
            abstract = abstracts.get(pmid, article.get('abstract', ''))
            
            pub_types = article.get('publication_types', [])
            evidence_level = EvidenceLevel.from_publication_type(pub_types)
            
            citation = Citation(
                pmid=pmid,
                title=article.get('title', ''),
                authors=article.get('authors', []),
                journal=article.get('journal', ''),
                year=article.get('year', ''),
                abstract=abstract,
                publication_types=pub_types,
                evidence_level=evidence_level,
                mesh_terms=article.get('mesh_terms', []),
                doi=article.get('doi')
            )
            citations.append(citation)
        
        if self.prefer_high_evidence:
            level_order = {
                EvidenceLevel.LEVEL_I: 0,
                EvidenceLevel.LEVEL_II: 1,
                EvidenceLevel.LEVEL_III: 2,
                EvidenceLevel.LEVEL_IV: 3,
                EvidenceLevel.LEVEL_V: 4,
                EvidenceLevel.UNKNOWN: 5
            }
            citations.sort(key=lambda c: level_order.get(c.evidence_level, 5))
        
        return citations
    
    def _synthesize_with_llm(
        self,
        citations: List[Citation],
        input_data: LiteratureInput
    ) -> Dict[str, str]:
        """Synthesize evidence using LLM"""
        try:
            from local_inference import grok_query
        except ImportError:
            return self._synthesize_fallback(citations, input_data)
        
        prompt = self._build_synthesis_prompt(citations, input_data)
        
        response = grok_query(
            prompt,
            temperature=0.1,
            max_tokens=800,
            model_name=self.model_name
        )
        
        return self._parse_synthesis_response(response, citations)
    
    def _build_synthesis_prompt(
        self,
        citations: List[Citation],
        input_data: LiteratureInput
    ) -> str:
        """Build the LLM synthesis prompt"""
        evidence_text = []
        for i, cit in enumerate(citations[:7], 1):
            abstract_preview = cit.abstract[:400] + '...' if len(cit.abstract) > 400 else cit.abstract
            evidence_text.append(
                f"{i}. [{cit.evidence_level.value}] {cit.format_ama()}\n"
                f"   Abstract: {abstract_preview}"
            )
        
        evidence_str = "\n\n".join(evidence_text)
        
        rec_context = ""
        if input_data.primary_recommendation:
            rec_context = f"\nRECOMMENDATION BEING EVALUATED:\n{input_data.primary_recommendation}\n"
        
        return f"""You are a clinical evidence synthesizer reviewing PubMed literature.

CLINICAL QUESTION:
{input_data.clinical_question}
{rec_context}
RETRIEVED EVIDENCE ({len(citations)} studies):

{evidence_str}

TASK: Synthesize the evidence to answer the clinical question.

Provide:
1. EVIDENCE SUMMARY (3-4 sentences): What does the literature say? Focus on findings from higher-level evidence (systematic reviews, RCTs) if available.

2. CLINICAL IMPLICATIONS (2-3 sentences): How should this evidence guide clinical decision-making?

3. LIMITATIONS (1-2 sentences): What are the key limitations or gaps in the evidence?

Format response as:
SUMMARY: [your synthesis]
IMPLICATIONS: [clinical guidance]
LIMITATIONS: [evidence gaps]"""
    
    def _parse_synthesis_response(
        self,
        response: str,
        citations: List[Citation]
    ) -> Dict[str, str]:
        """Parse LLM synthesis response"""
        summary = ""
        implications = ""
        limitations = ""
        
        lines = response.split('\n')
        current_section = None
        
        for line in lines:
            line_stripped = line.strip()
            line_lower = line_stripped.lower()
            
            if line_lower.startswith('summary:'):
                current_section = 'summary'
                summary = line_stripped[8:].strip()
            elif line_lower.startswith('implications:') or line_lower.startswith('clinical implications:'):
                current_section = 'implications'
                idx = line_lower.find(':')
                implications = line_stripped[idx+1:].strip()
            elif line_lower.startswith('limitations:'):
                current_section = 'limitations'
                limitations = line_stripped[12:].strip()
            elif current_section and line_stripped:
                if current_section == 'summary':
                    summary += ' ' + line_stripped
                elif current_section == 'implications':
                    implications += ' ' + line_stripped
                elif current_section == 'limitations':
                    limitations += ' ' + line_stripped
        
        if not summary:
            summary = response[:500] if response else "Unable to synthesize evidence."
        
        notes_parts = []
        if implications:
            notes_parts.append(f"Clinical Implications: {implications}")
        if limitations:
            notes_parts.append(f"Limitations: {limitations}")
        
        return {
            'summary': summary.strip(),
            'notes': ' | '.join(notes_parts) if notes_parts else "See individual citations for details."
        }
    
    def _synthesize_fallback(
        self,
        citations: List[Citation],
        input_data: LiteratureInput
    ) -> Dict[str, str]:
        """Fallback synthesis when LLM unavailable"""
        if not citations:
            return {
                'summary': "No relevant literature found for this clinical question.",
                'notes': "Consider broadening search terms or consulting additional sources."
            }
        
        level_counts = {}
        for cit in citations:
            level = cit.evidence_level.value
            level_counts[level] = level_counts.get(level, 0) + 1
        
        highest = self._get_highest_evidence_level(citations)
        
        summary_parts = [
            f"Retrieved {len(citations)} relevant studies.",
            f"Highest evidence level: {highest.value}."
        ]
        
        if highest in [EvidenceLevel.LEVEL_I, EvidenceLevel.LEVEL_II]:
            summary_parts.append("High-quality evidence available to guide decision-making.")
        elif highest == EvidenceLevel.LEVEL_III:
            summary_parts.append("Moderate-quality evidence available. Consider with clinical judgment.")
        else:
            summary_parts.append("Limited high-quality evidence. Rely on clinical expertise.")
        
        top_citations = [cit.format_short() for cit in citations[:3]]
        summary_parts.append(f"Key references: {'; '.join(top_citations)}.")
        
        level_summary = ", ".join([f"{k}: {v}" for k, v in level_counts.items()])
        
        return {
            'summary': ' '.join(summary_parts),
            'notes': f"Evidence distribution: {level_summary}"
        }
    
    def _generate_fallback_result(
        self,
        input_data: LiteratureInput,
        search_query: str,
        pubmed_available: bool,
        elapsed_time: float
    ) -> LiteratureResult:
        """Generate fallback result when PubMed unavailable or no results"""
        if not pubmed_available:
            summary = "PubMed API is currently unavailable. Literature search could not be performed."
            notes = "Recommend manual literature review or retry later."
        else:
            summary = "No relevant literature found for the search query."
            notes = "Consider broadening search terms or using alternative databases."
        
        return LiteratureResult(
            clinical_question=input_data.clinical_question,
            search_query=search_query,
            citations=[],
            evidence_summary=summary,
            highest_evidence_level=EvidenceLevel.UNKNOWN,
            evidence_distribution={},
            supports_recommendation=False,
            confidence_score=0.0,
            synthesis_notes=notes,
            timestamp=datetime.utcnow().isoformat() + "Z",
            hash=self._compute_hash(input_data, summary),
            pubmed_available=pubmed_available,
            model_used=None,
            latency_ms=elapsed_time * 1000
        )
    
    def _calculate_evidence_distribution(
        self,
        citations: List[Citation]
    ) -> Dict[str, int]:
        """Calculate distribution of evidence levels"""
        distribution = {}
        for cit in citations:
            level = cit.evidence_level.value
            distribution[level] = distribution.get(level, 0) + 1
        return distribution
    
    def _get_highest_evidence_level(
        self,
        citations: List[Citation]
    ) -> EvidenceLevel:
        """Get the highest evidence level from citations"""
        if not citations:
            return EvidenceLevel.UNKNOWN
        
        level_priority = [
            EvidenceLevel.LEVEL_I,
            EvidenceLevel.LEVEL_II,
            EvidenceLevel.LEVEL_III,
            EvidenceLevel.LEVEL_IV,
            EvidenceLevel.LEVEL_V
        ]
        
        for level in level_priority:
            if any(cit.evidence_level == level for cit in citations):
                return level
        
        return EvidenceLevel.UNKNOWN
    
    def _calculate_confidence(
        self,
        citations: List[Citation],
        highest_level: EvidenceLevel
    ) -> float:
        """Calculate confidence score based on evidence quality"""
        if not citations:
            return 0.0
        
        level_scores = {
            EvidenceLevel.LEVEL_I: 0.95,
            EvidenceLevel.LEVEL_II: 0.85,
            EvidenceLevel.LEVEL_III: 0.70,
            EvidenceLevel.LEVEL_IV: 0.55,
            EvidenceLevel.LEVEL_V: 0.40,
            EvidenceLevel.UNKNOWN: 0.30
        }
        
        base_score = level_scores.get(highest_level, 0.30)
        
        volume_bonus = min(len(citations) * 0.02, 0.15)
        
        high_evidence_count = sum(
            1 for c in citations 
            if c.evidence_level in [EvidenceLevel.LEVEL_I, EvidenceLevel.LEVEL_II]
        )
        consistency_bonus = min(high_evidence_count * 0.03, 0.10)
        
        return min(base_score + volume_bonus + consistency_bonus, 0.99)
    
    def _assess_recommendation_support(
        self,
        citations: List[Citation],
        recommendation: Optional[str]
    ) -> bool:
        """Assess whether evidence supports the recommendation"""
        if not recommendation or not citations:
            return False
        
        rec_lower = recommendation.lower()
        
        support_count = 0
        for cit in citations:
            abstract_lower = cit.abstract.lower()
            
            positive_terms = ['effective', 'beneficial', 'recommended', 'improves', 'reduces']
            negative_terms = ['not recommended', 'ineffective', 'no benefit', 'harmful']
            
            has_positive = any(term in abstract_lower for term in positive_terms)
            has_negative = any(term in abstract_lower for term in negative_terms)
            
            if has_positive and not has_negative:
                support_count += 1
        
        return support_count >= len(citations) / 2 if citations else False
    
    def _compute_hash(
        self,
        input_data: LiteratureInput,
        synthesis: str
    ) -> str:
        """Compute hash for audit trail"""
        data = {
            'question': input_data.clinical_question,
            'synthesis': synthesis,
            'timestamp': datetime.utcnow().isoformat()
        }
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()


def run_literature_analysis(
    clinical_question: str,
    patient_context: Dict[str, Any],
    primary_recommendation: Optional[str] = None,
    max_results: int = 10,
    use_llm: bool = True,
    model_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to run literature analysis.
    
    Args:
        clinical_question: The clinical question to research
        patient_context: Patient demographics and clinical data
        primary_recommendation: Optional recommendation to evaluate
        max_results: Maximum citations to retrieve
        use_llm: Whether to use LLM for synthesis
        model_name: Optional specific model to use
        
    Returns:
        Dict containing literature analysis results
        
    Example:
        result = run_literature_analysis(
            clinical_question="What is the optimal anticoagulation for atrial fibrillation?",
            patient_context={"age": 72, "gender": "M", "conditions": ["hypertension"]},
            primary_recommendation="Apixaban 5mg BID"
        )
    """
    stage = LiteratureStage(
        use_llm=use_llm,
        model_name=model_name,
        max_results=max_results
    )
    
    input_data = LiteratureInput(
        clinical_question=clinical_question,
        patient_context=patient_context,
        primary_recommendation=primary_recommendation,
        max_results=max_results
    )
    
    result = stage.analyze(input_data)
    return result.to_dict()
