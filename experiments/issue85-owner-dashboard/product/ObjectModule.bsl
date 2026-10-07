#If Server Or ExternalConnection Then

#Region Public

// Read-only summary in the accounting currency; EndDateExclusive is not included.
// Products contains all rows, not only the five displayed by the dashboard.
Function GetYesterdaySummary(AsOfDate = Undefined) Export

	If Not AccessRight("Read", Metadata.AccumulationRegisters.Sales)
		Or Not AccessRight("Read", Metadata.AccumulationRegisters.InventoryCost)
		Or Not AccessRight("Read", Metadata.Documents.SalesInvoice)
		Or Not AccessRight("Read", Metadata.Catalogs.Products) Then
		Raise NStr("en = 'Insufficient rights to read the sales dashboard.'; tr = 'Satış kontrol panelini okumak için yeterli yetki yok.'");
	EndIf;

	If AsOfDate = Undefined Then
		AsOfDate = CurrentSessionDate();
	EndIf;
	EndDateExclusive = BegOfDay(AsOfDate);
	StartDate = EndDateExclusive - 86400;

	// UNION ALL prevents multiplication of sales and cost records for one product.
	Query = New Query;
	Query.Text =
	"SELECT ALLOWED
	| Movements.Product AS Product,
	| SUM(Movements.Revenue) AS Revenue,
	| SUM(Movements.VAT) AS VAT,
	| SUM(Movements.Cost) AS Cost,
	| SUM(Movements.Revenue) - SUM(Movements.Cost) AS GrossProfit
	|FROM
	| (SELECT
	|   Sales.Product AS Product,
	|   Sales.Amount AS Revenue,
	|   Sales.VATAmount AS VAT,
	|   0 AS Cost
	|  FROM AccumulationRegister.Sales AS Sales
	|  WHERE Sales.Active
	|   AND Sales.Recorder REFS Document.SalesInvoice
	|   AND Sales.Recorder.Posted
	|   AND Sales.Period >= &StartDate
	|   AND Sales.Period < &EndDateExclusive
	|
	|  UNION ALL
	|
	|  SELECT
	|   InventoryCost.Product,
	|   0,
	|   0,
	|   InventoryCost.Amount
	|  FROM AccumulationRegister.InventoryCost AS InventoryCost
	|  WHERE InventoryCost.Active
	|   AND InventoryCost.Recorder REFS Document.SalesInvoice
	|   AND InventoryCost.Recorder.Posted
	|   AND InventoryCost.RecordType = VALUE(AccumulationRecordType.Expense)
	|   AND InventoryCost.Period >= &StartDate
	|   AND InventoryCost.Period < &EndDateExclusive) AS Movements
	|GROUP BY
	| Movements.Product,
	| Movements.Product.Code
	|ORDER BY
	| Revenue DESC,
	| Movements.Product.Code,
	| Movements.Product
	|;
	|
	|SELECT ALLOWED
	| COUNT(DISTINCT Sales.Recorder) AS InvoiceCount
	|FROM AccumulationRegister.Sales AS Sales
	|WHERE Sales.Active
	| AND Sales.Recorder REFS Document.SalesInvoice
	| AND Sales.Recorder.Posted
	| AND Sales.Period >= &StartDate
	| AND Sales.Period < &EndDateExclusive";
	Query.SetParameter("StartDate", StartDate);
	Query.SetParameter("EndDateExclusive", EndDateExclusive);
	Results = Query.ExecuteBatch();
	Products = Results[0].Unload();
	InvoiceSelection = Results[1].Select();
	InvoiceSelection.Next();

	Summary = New Structure;
	Summary.Insert("StartDate", StartDate);
	Summary.Insert("EndDateExclusive", EndDateExclusive);
	Summary.Insert("Revenue", 0);
	Summary.Insert("VAT", 0);
	Summary.Insert("Cost", 0);
	For Each ProductRow In Products Do
		Summary.Revenue = Summary.Revenue + ProductRow.Revenue;
		Summary.VAT = Summary.VAT + ProductRow.VAT;
		Summary.Cost = Summary.Cost + ProductRow.Cost;
	EndDo;
	Summary.Insert("GrossSales", Summary.Revenue + Summary.VAT);
	Summary.Insert("GrossProfit", Summary.Revenue - Summary.Cost);
	Summary.Insert("InvoiceCount", InvoiceSelection.InvoiceCount);
	Summary.Insert("AverageTicket", 0);
	If Summary.InvoiceCount > 0 Then
		Summary.AverageTicket = Round(Summary.Revenue / Summary.InvoiceCount, 2);
	EndIf;
	Summary.Insert("Products", Products);
	Return Summary;

EndFunction

Function RenderYesterdayDashboard(Summary) Export

	Dashboard = New SpreadsheetDocument;
	Dashboard.Area(1, 1).Text = NStr("en = 'Yesterday — owner dashboard'; tr = 'Dün — işletme sahibi kontrol paneli'");
	Dashboard.Area(2, 1).Text = NStr("en = 'Trading date'; tr = 'İşlem tarihi'");
	Dashboard.Area(2, 2).Text = Format(Summary.StartDate, "DF=yyyy-MM-dd");
	Dashboard.Area(3, 1).Text = NStr("en = 'All amounts in accounting currency'; tr = 'Tüm tutarlar muhasebe para birimindedir'");

	Dashboard.Area(5, 1).Text = NStr("en = 'Sales excluding VAT'; tr = 'KDV hariç satışlar'");
	Dashboard.Area(5, 2).Text = Format(Summary.Revenue, "NFD=2;NZ=0");
	Dashboard.Area(6, 1).Text = NStr("en = 'VAT'; tr = 'KDV'");
	Dashboard.Area(6, 2).Text = Format(Summary.VAT, "NFD=2;NZ=0");
	Dashboard.Area(7, 1).Text = NStr("en = 'Sales including VAT'; tr = 'KDV dahil satışlar'");
	Dashboard.Area(7, 2).Text = Format(Summary.GrossSales, "NFD=2;NZ=0");
	Dashboard.Area(8, 1).Text = NStr("en = 'Cost of goods sold'; tr = 'Satılan malların maliyeti'");
	Dashboard.Area(8, 2).Text = Format(Summary.Cost, "NFD=2;NZ=0");
	Dashboard.Area(9, 1).Text = NStr("en = 'Gross profit (not net profit)'; tr = 'Brüt kâr (net kâr değil)'");
	Dashboard.Area(9, 2).Text = Format(Summary.GrossProfit, "NFD=2;NZ=0");
	Dashboard.Area(10, 1).Text = NStr("en = 'Posted sales invoices'; tr = 'Kaydedilmiş satış faturaları'");
	Dashboard.Area(10, 2).Text = Format(Summary.InvoiceCount, "NFD=0;NZ=0");
	Dashboard.Area(11, 1).Text = NStr("en = 'Average invoice excluding VAT'; tr = 'KDV hariç ortalama fatura'");
	Dashboard.Area(11, 2).Text = Format(Summary.AverageTicket, "NFD=2;NZ=0");
	Dashboard.Area(13, 1).Text = NStr("en = 'Gross profit excludes business expenses and payments.'; tr = 'Brüt kâr işletme giderlerini ve ödemeleri içermez.'");
	If Summary.InvoiceCount = 0 Then
		Dashboard.Area(14, 1).Text = NStr("en = 'No posted sales for yesterday.'; tr = 'Dün için kaydedilmiş satış yok.'");
	EndIf;

	Dashboard.Area(16, 1).Text = NStr("en = 'Top 5 products by sales excluding VAT'; tr = 'KDV hariç satışlara göre ilk 5 ürün'");
	Dashboard.Area(17, 1).Text = NStr("en = 'Product'; tr = 'Ürün'");
	Dashboard.Area(17, 2).Text = NStr("en = 'Sales excluding VAT'; tr = 'KDV hariç satışlar'");
	Dashboard.Area(17, 3).Text = NStr("en = 'VAT'; tr = 'KDV'");
	Dashboard.Area(17, 4).Text = NStr("en = 'Cost'; tr = 'Maliyet'");
	Dashboard.Area(17, 5).Text = NStr("en = 'Gross profit'; tr = 'Brüt kâr'");
	RowNumber = 18;
	For Each ProductRow In Summary.Products Do
		If RowNumber > 22 Then
			Break;
		EndIf;
		Dashboard.Area(RowNumber, 1).Text = String(ProductRow.Product);
		Dashboard.Area(RowNumber, 2).Text = Format(ProductRow.Revenue, "NFD=2;NZ=0");
		Dashboard.Area(RowNumber, 3).Text = Format(ProductRow.VAT, "NFD=2;NZ=0");
		Dashboard.Area(RowNumber, 4).Text = Format(ProductRow.Cost, "NFD=2;NZ=0");
		Dashboard.Area(RowNumber, 5).Text = Format(ProductRow.GrossProfit, "NFD=2;NZ=0");
		RowNumber = RowNumber + 1;
	EndDo;
	Dashboard.Area(1, 1, 22, 1).ColumnWidth = 60;
	Dashboard.Area(1, 2, 22, 5).ColumnWidth = 22;
	Return Dashboard;

EndFunction

#EndRegion

#EndIf
