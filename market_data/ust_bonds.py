from dataclasses import dataclass
from typing import Optional
import requests
from dataclasses import dataclass
import datetime as dt
from ibapi.contract import ContractDetails, Contract


@dataclass
class USTreasurySecurity:
    cusip: str
    issueDate: dt.date
    securityType: str
    securityTerm: str
    maturityDate: dt.date
    interestRate: str
    refCpiOnIssueDate: str
    refCpiOnDatedDate: str
    announcementDate: str
    auctionDate: str
    auctionDateYear: dt.date
    datedDate: object
    accruedInterestPer1000: str
    accruedInterestPer100: str
    adjustedAccruedInterestPer1000: str
    adjustedPrice: str
    allocationPercentage: str
    allocationPercentageDecimals: str
    announcedCusip: str
    auctionFormat: str
    averageMedianDiscountRate: str
    averageMedianInvestmentRate: str
    averageMedianPrice: str
    averageMedianDiscountMargin: str
    averageMedianYield: str
    backDated: str
    backDatedDate: object
    bidToCoverRatio: str
    callDate: str
    callable: str
    calledDate: str
    cashManagementBillCMB: str
    closingTimeCompetitive: str
    closingTimeNoncompetitive: str
    competitiveAccepted: str
    competitiveBidDecimals: str
    competitiveTendered: str
    competitiveTendersAccepted: str
    corpusCusip: str
    cpiBaseReferencePeriod: str
    currentlyOutstanding: str
    directBidderAccepted: str
    directBidderTendered: str
    estimatedAmountOfPubliclyHeldMaturingSecuritiesByType: str
    fimaIncluded: str
    fimaNoncompetitiveAccepted: str
    fimaNoncompetitiveTendered: str
    firstInterestPeriod: str
    firstInterestPaymentDate: object
    floatingRate: str
    frnIndexDeterminationDate: object
    frnIndexDeterminationRate: str
    highDiscountRate: str
    highInvestmentRate: str
    highPrice: str
    highDiscountMargin: str
    highYield: str
    indexRatioOnIssueDate: str
    indirectBidderAccepted: str
    indirectBidderTendered: str
    interestPaymentFrequency: str
    lowDiscountRate: str
    lowInvestmentRate: str
    lowPrice: str
    lowDiscountMargin: str
    lowYield: str
    maturingDate: str
    maximumCompetitiveAward: str
    maximumNoncompetitiveAward: str
    maximumSingleBid: str
    minimumBidAmount: str
    minimumStripAmount: str
    minimumToIssue: str
    multiplesToBid: str
    multiplesToIssue: str
    nlpExclusionAmount: str
    nlpReportingThreshold: str
    noncompetitiveAccepted: str
    noncompetitiveTendersAccepted: str
    offeringAmount: str
    originalCusip: str
    originalDatedDate: object
    originalIssueDate: object
    originalSecurityTerm: str
    pdfFilenameAnnouncement: str
    pdfFilenameCompetitiveResults: str
    pdfFilenameNoncompetitiveResults: str
    pdfFilenameSpecialAnnouncement: str
    pricePer100: str
    primaryDealerAccepted: str
    primaryDealerTendered: str
    reopening: str
    securityTermDayMonth: str
    securityTermWeekYear: str
    series: str
    somaAccepted: str
    somaHoldings: str
    somaIncluded: str
    somaTendered: str
    spread: str
    standardInterestPaymentPer1000: str
    strippable: str
    term: str
    tiinConversionFactorPer1000: str
    tips: str
    totalAccepted: str
    totalTendered: str
    treasuryDirectAccepted: str
    treasuryDirectTendersAccepted: str
    type: str
    unadjustedAccruedInterestPer1000: str
    unadjustedPrice: str
    updatedTimestamp: str
    xmlFilenameAnnouncement: str
    xmlFilenameCompetitiveResults: str
    xmlFilenameSpecialAnnouncement: str
    tintCusip1: str
    tintCusip2: str
    contract_details: Optional[ContractDetails] = None

    def days_since_issued(self) -> int:
        return (dt.datetime.now().date() - self.issueDate).days

    def days_to_next_payment(self) -> int:
        next_payment_date = (self.issueDate + dt.timedelta(weeks=24))
        days_until_next_payment = (
            next_payment_date - dt.datetime.now().date()).days
        return days_until_next_payment

    def summarize(self) -> dict[str, str]:
        return {'cusip': self.cusip, 'security_term': str(self.securityTerm), 'issue_date': str(self.issueDate), 'interest_rate': str(self.interestRate), 'days_since_issued': str(self.days_since_issued()), 'days_to_next_payment': str(self.days_to_next_payment())}

    def __eq__(self, other) -> bool:
        return self.securityTerm == other.securityTerm

    def __hash__(self) -> int:
        return hash(self.securityTerm)

    def to_ibkr_contract(self) -> Contract:
        """Assembles contract object for a bond,using the cusip as the symbol"""
        contract = Contract()
        contract.secType = 'BOND'
        contract.currency = 'USD'
        contract.exchange = 'SMART'
        contract.symbol = self.cusip
        return contract

    @staticmethod
    def from_dict(obj: object) -> 'USTreasurySecurity':
        _cusip = str(obj.get("cusip"))
        # 2022-05-31T00:00:00
        # %Y-%m-%dT%H:%M:%S
        _issueDate = dt.datetime.strptime(
            str(obj.get("issueDate")), '%Y-%m-%dT%H:%M:%S').date()
        _securityType = str(obj.get("securityType"))
        _securityTerm = str(obj.get("securityTerm"))
        _maturityDate = dt.datetime.strptime(
            str(obj.get("maturityDate")), '%Y-%m-%dT%H:%M:%S').date()
        _interestRate = str(obj.get("interestRate"))
        _refCpiOnIssueDate = str(obj.get("refCpiOnIssueDate"))
        _refCpiOnDatedDate = str(obj.get("refCpiOnDatedDate"))
        _announcementDate = str(obj.get("announcementDate"))
        _auctionDate = dt.datetime.strptime(
            str(obj.get("auctionDate")), '%Y-%m-%dT%H:%M:%S').date()
        _auctionDateYear = str(obj.get("auctionDateYear"))
        _datedDate = str(obj.get("datedDate"))
        _accruedInterestPer1000 = str(obj.get("accruedInterestPer1000"))
        _accruedInterestPer100 = str(obj.get("accruedInterestPer100"))
        _adjustedAccruedInterestPer1000 = str(
            obj.get("adjustedAccruedInterestPer1000"))
        _adjustedPrice = str(obj.get("adjustedPrice"))
        _allocationPercentage = str(obj.get("allocationPercentage"))
        _allocationPercentageDecimals = str(
            obj.get("allocationPercentageDecimals"))
        _announcedCusip = str(obj.get("announcedCusip"))
        _auctionFormat = str(obj.get("auctionFormat"))
        _averageMedianDiscountRate = str(obj.get("averageMedianDiscountRate"))
        _averageMedianInvestmentRate = str(
            obj.get("averageMedianInvestmentRate"))
        _averageMedianPrice = str(obj.get("averageMedianPrice"))
        _averageMedianDiscountMargin = str(
            obj.get("averageMedianDiscountMargin"))
        _averageMedianYield = str(obj.get("averageMedianYield"))
        _backDated = str(obj.get("backDated"))
        _backDatedDate = str(obj.get("backDatedDate"))
        _bidToCoverRatio = str(obj.get("bidToCoverRatio"))
        _callDate = str(obj.get("callDate"))
        _callable = str(obj.get("callable"))
        _calledDate = str(obj.get("calledDate"))
        _cashManagementBillCMB = str(obj.get("cashManagementBillCMB"))
        _closingTimeCompetitive = str(obj.get("closingTimeCompetitive"))
        _closingTimeNoncompetitive = str(obj.get("closingTimeNoncompetitive"))
        _competitiveAccepted = str(obj.get("competitiveAccepted"))
        _competitiveBidDecimals = str(obj.get("competitiveBidDecimals"))
        _competitiveTendered = str(obj.get("competitiveTendered"))
        _competitiveTendersAccepted = str(
            obj.get("competitiveTendersAccepted"))
        _corpusCusip = str(obj.get("corpusCusip"))
        _cpiBaseReferencePeriod = str(obj.get("cpiBaseReferencePeriod"))
        _currentlyOutstanding = str(obj.get("currentlyOutstanding"))
        _directBidderAccepted = str(obj.get("directBidderAccepted"))
        _directBidderTendered = str(obj.get("directBidderTendered"))
        _estimatedAmountOfPubliclyHeldMaturingSecuritiesByType = str(
            obj.get("estimatedAmountOfPubliclyHeldMaturingSecuritiesByType"))
        _fimaIncluded = str(obj.get("fimaIncluded"))
        _fimaNoncompetitiveAccepted = str(
            obj.get("fimaNoncompetitiveAccepted"))
        _fimaNoncompetitiveTendered = str(
            obj.get("fimaNoncompetitiveTendered"))
        _firstInterestPeriod = str(obj.get("firstInterestPeriod"))
        _firstInterestPaymentDate = str(obj.get("firstInterestPaymentDate"))
        _floatingRate = str(obj.get("floatingRate"))
        _frnIndexDeterminationDate = str(obj.get("frnIndexDeterminationDate"))
        _frnIndexDeterminationRate = str(obj.get("frnIndexDeterminationRate"))
        _highDiscountRate = str(obj.get("highDiscountRate"))
        _highInvestmentRate = str(obj.get("highInvestmentRate"))
        _highPrice = str(obj.get("highPrice"))
        _highDiscountMargin = str(obj.get("highDiscountMargin"))
        _highYield = str(obj.get("highYield"))
        _indexRatioOnIssueDate = str(obj.get("indexRatioOnIssueDate"))
        _indirectBidderAccepted = str(obj.get("indirectBidderAccepted"))
        _indirectBidderTendered = str(obj.get("indirectBidderTendered"))
        _interestPaymentFrequency = str(obj.get("interestPaymentFrequency"))
        _lowDiscountRate = str(obj.get("lowDiscountRate"))
        _lowInvestmentRate = str(obj.get("lowInvestmentRate"))
        _lowPrice = str(obj.get("lowPrice"))
        _lowDiscountMargin = str(obj.get("lowDiscountMargin"))
        _lowYield = str(obj.get("lowYield"))
        _maturingDate = str(obj.get("maturingDate"))
        _maximumCompetitiveAward = str(obj.get("maximumCompetitiveAward"))
        _maximumNoncompetitiveAward = str(
            obj.get("maximumNoncompetitiveAward"))
        _maximumSingleBid = str(obj.get("maximumSingleBid"))
        _minimumBidAmount = str(obj.get("minimumBidAmount"))
        _minimumStripAmount = str(obj.get("minimumStripAmount"))
        _minimumToIssue = str(obj.get("minimumToIssue"))
        _multiplesToBid = str(obj.get("multiplesToBid"))
        _multiplesToIssue = str(obj.get("multiplesToIssue"))
        _nlpExclusionAmount = str(obj.get("nlpExclusionAmount"))
        _nlpReportingThreshold = str(obj.get("nlpReportingThreshold"))
        _noncompetitiveAccepted = str(obj.get("noncompetitiveAccepted"))
        _noncompetitiveTendersAccepted = str(
            obj.get("noncompetitiveTendersAccepted"))
        _offeringAmount = str(obj.get("offeringAmount"))
        _originalCusip = str(obj.get("originalCusip"))
        _originalDatedDate = str(obj.get("originalDatedDate"))
        _originalIssueDate = str(obj.get("originalIssueDate"))
        _originalSecurityTerm = str(obj.get("originalSecurityTerm"))
        _pdfFilenameAnnouncement = str(obj.get("pdfFilenameAnnouncement"))
        _pdfFilenameCompetitiveResults = str(
            obj.get("pdfFilenameCompetitiveResults"))
        _pdfFilenameNoncompetitiveResults = str(
            obj.get("pdfFilenameNoncompetitiveResults"))
        _pdfFilenameSpecialAnnouncement = str(
            obj.get("pdfFilenameSpecialAnnouncement"))
        _pricePer100 = str(obj.get("pricePer100"))
        _primaryDealerAccepted = str(obj.get("primaryDealerAccepted"))
        _primaryDealerTendered = str(obj.get("primaryDealerTendered"))
        _reopening = str(obj.get("reopening"))
        _securityTermDayMonth = str(obj.get("securityTermDayMonth"))
        _securityTermWeekYear = str(obj.get("securityTermWeekYear"))
        _series = str(obj.get("series"))
        _somaAccepted = str(obj.get("somaAccepted"))
        _somaHoldings = str(obj.get("somaHoldings"))
        _somaIncluded = str(obj.get("somaIncluded"))
        _somaTendered = str(obj.get("somaTendered"))
        _spread = str(obj.get("spread"))
        _standardInterestPaymentPer1000 = str(
            obj.get("standardInterestPaymentPer1000"))
        _strippable = str(obj.get("strippable"))
        _term = str(obj.get("term"))
        _tiinConversionFactorPer1000 = str(
            obj.get("tiinConversionFactorPer1000"))
        _tips = str(obj.get("tips"))
        _totalAccepted = str(obj.get("totalAccepted"))
        _totalTendered = str(obj.get("totalTendered"))
        _treasuryDirectAccepted = str(obj.get("treasuryDirectAccepted"))
        _treasuryDirectTendersAccepted = str(
            obj.get("treasuryDirectTendersAccepted"))
        _type = str(obj.get("type"))
        _unadjustedAccruedInterestPer1000 = str(
            obj.get("unadjustedAccruedInterestPer1000"))
        _unadjustedPrice = str(obj.get("unadjustedPrice"))
        _updatedTimestamp = str(obj.get("updatedTimestamp"))
        _xmlFilenameAnnouncement = str(obj.get("xmlFilenameAnnouncement"))
        _xmlFilenameCompetitiveResults = str(
            obj.get("xmlFilenameCompetitiveResults"))
        _xmlFilenameSpecialAnnouncement = str(
            obj.get("xmlFilenameSpecialAnnouncement"))
        _tintCusip1 = str(obj.get("tintCusip1"))
        _tintCusip2 = str(obj.get("tintCusip2"))
        return USTreasurySecurity(_cusip, _issueDate, _securityType, _securityTerm, _maturityDate, _interestRate, _refCpiOnIssueDate, _refCpiOnDatedDate, _announcementDate, _auctionDate, _auctionDateYear, _datedDate, _accruedInterestPer1000, _accruedInterestPer100, _adjustedAccruedInterestPer1000, _adjustedPrice, _allocationPercentage, _allocationPercentageDecimals, _announcedCusip, _auctionFormat, _averageMedianDiscountRate, _averageMedianInvestmentRate, _averageMedianPrice, _averageMedianDiscountMargin, _averageMedianYield, _backDated, _backDatedDate, _bidToCoverRatio, _callDate, _callable, _calledDate, _cashManagementBillCMB, _closingTimeCompetitive, _closingTimeNoncompetitive, _competitiveAccepted, _competitiveBidDecimals, _competitiveTendered, _competitiveTendersAccepted, _corpusCusip, _cpiBaseReferencePeriod, _currentlyOutstanding, _directBidderAccepted, _directBidderTendered, _estimatedAmountOfPubliclyHeldMaturingSecuritiesByType, _fimaIncluded, _fimaNoncompetitiveAccepted, _fimaNoncompetitiveTendered, _firstInterestPeriod, _firstInterestPaymentDate, _floatingRate, _frnIndexDeterminationDate, _frnIndexDeterminationRate, _highDiscountRate, _highInvestmentRate, _highPrice, _highDiscountMargin, _highYield, _indexRatioOnIssueDate, _indirectBidderAccepted, _indirectBidderTendered, _interestPaymentFrequency, _lowDiscountRate, _lowInvestmentRate, _lowPrice, _lowDiscountMargin, _lowYield, _maturingDate, _maximumCompetitiveAward, _maximumNoncompetitiveAward, _maximumSingleBid, _minimumBidAmount, _minimumStripAmount, _minimumToIssue, _multiplesToBid, _multiplesToIssue, _nlpExclusionAmount, _nlpReportingThreshold, _noncompetitiveAccepted, _noncompetitiveTendersAccepted, _offeringAmount, _originalCusip, _originalDatedDate, _originalIssueDate, _originalSecurityTerm, _pdfFilenameAnnouncement, _pdfFilenameCompetitiveResults, _pdfFilenameNoncompetitiveResults, _pdfFilenameSpecialAnnouncement, _pricePer100, _primaryDealerAccepted, _primaryDealerTendered, _reopening, _securityTermDayMonth, _securityTermWeekYear, _series, _somaAccepted, _somaHoldings, _somaIncluded, _somaTendered, _spread, _standardInterestPaymentPer1000, _strippable, _term, _tiinConversionFactorPer1000, _tips, _totalAccepted, _totalTendered, _treasuryDirectAccepted, _treasuryDirectTendersAccepted, _type, _unadjustedAccruedInterestPer1000, _unadjustedPrice, _updatedTimestamp, _xmlFilenameAnnouncement, _xmlFilenameCompetitiveResults, _xmlFilenameSpecialAnnouncement, _tintCusip1, _tintCusip2)


def get_securities(params: dict[str, str]) -> Optional[list[USTreasurySecurity]]:
    url = 'http://www.treasurydirect.gov/TA_WS/securities/auctioned'
    request = requests.get(url, params=params)
    if request.status_code == 200:
        securities = []
        for security in request.json():
            securities.append(USTreasurySecurity.from_dict(security))
        return securities
    else:
        return None


def get_bonds_info() -> Optional[list[USTreasurySecurity]]:
    terms = ['2-Year', '5-Year', '10-Year', '30-Year', '20-Year']
    types = ['Note', 'Bond', 'Bill']
    securities = get_securities(params={'format': 'json', 'days': '365'})
    if securities is not None:
        securities = [s for s in securities if s.type in types and s.securityTerm in terms and s.days_since_issued(
        ) > 14 and s.days_to_next_payment() > 14]
        securities.sort(key=lambda s: s.days_since_issued())
        seen_titles = set()
        new_list = []
        for obj in securities:
            if obj.securityTerm not in seen_titles:
                new_list.append(obj)
                seen_titles.add(obj.securityTerm)
        return new_list
    else:
        return None
