&AtServer
Procedure OnCreateAtServer(Cancel, StandardProcessing)

	GenerateAtServer();

EndProcedure

&AtClient
Procedure Refresh(Command)

	GenerateAtServer();

EndProcedure

&AtServer
Procedure GenerateAtServer()

	ReportObject = FormAttributeToValue("Report");
	Summary = ReportObject.GetYesterdaySummary();
	OwnerDashboard = ReportObject.RenderYesterdayDashboard(Summary);

EndProcedure
