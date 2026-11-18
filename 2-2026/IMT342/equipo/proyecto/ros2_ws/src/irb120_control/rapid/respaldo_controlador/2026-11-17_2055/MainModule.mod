MODULE MainModule
	TASK PERS tooldata tool1:=[TRUE,[[0,0,130],[1,0,0,0]],[0.21,[0,0,0],[1,0,0,0],0,0,0]];
	CONST robtarget pHome:=[[311.84,223.25,671.10],[0.138133,-0.870533,-0.307562,-0.358466],[0,0,1,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
	CONST robtarget p10:=[[338.34,22.41,671.08],[0.138135,-0.870556,-0.307561,-0.358409],[-1,0,1,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
	CONST robtarget p20:=[[169.93,325.00,668.85],[0.138091,-0.870618,-0.307411,-0.358405],[0,-1,2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
	PROC main()
		MoveJ pHome, v200, z50, tool1;
		MoveJ p10, v200, z50, tool1;
		MoveJ p20, v200, z50, tool1;
		MoveJ p10, v200, z50, tool1;
		MoveJ p20, v200, z50, tool1;
		MoveJ p10, v200, z50, tool1;
		MoveJ p20, v200, z50, tool1;
		MoveJ pHome, v200, z50, tool1;
	ENDPROC
ENDMODULE