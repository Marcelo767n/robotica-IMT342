MODULE Module1
    RECORD SquareMapType
        robtarget safe;
        robtarget final;
    ENDRECORD
    VAR SquareMapType Squares{79};
    CONST robtarget Target_10:=[[0,300,390],[0,-0.707106781,0.707106781,0],[1,0,-1,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget Target_70:=[[209,209,180],[0,-0.707106781,0.707106781,0],[0,0,-1,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget Target_30:=[[-27.5,-5.25,-16],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget Target_40:=[[393,-21.5,-14],[0.055478959,-0.704927007,0.704927007,-0.055478959],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget Target_50:=[[411.5,395.75,-9],[0.055478959,-0.704927007,0.704927007,-0.055478959],[0,-1,-1,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget Target_60:=[[-3,411.7,-14],[0,-0.707106781,0.707106781,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget A1:=[[379,26.5,-7],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget PSegHome:=[[0,300,390],[0,-0.707106781,0.707106781,0],[1,0,-1,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget PSegCenter:=[[209,209,180],[0,-0.707106781,0.707106781,0],[0,0,-1,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget PSeg1:=[[87.5,100.75,180],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget PSeg2:=[[299.5,103.75,181.5],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget PSeg3:=[[298.5,313.75,183.5],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget PSeg4:=[[91,310.25,180.5],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget E1:=[[377.5,235.5,-1],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget E2:=[[324.5,235.5,-1],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget E3:=[[272.5,235,-2],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget E4:=[[220.5,234,-1],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget A2:=[[325.5,25.5,-3],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget A3:=[[273,25.5,-3],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget A4:=[[220.5,25.5,-3],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget A5:=[[168,24.5,-5],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget A6:=[[114.5,25,-5],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget A7:=[[62,24.5,-5],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget A8:=[[8,23.5,-4],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget B1:=[[378,78.5,-2],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget B2:=[[326,77.5,-3],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget B3:=[[272.5,78,-2],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget B4:=[[221,77.5,-3],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget B5:=[[168.5,77,-4],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget B6:=[[115,76,-5],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget B7:=[[62,75,-3],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget B8:=[[6.5,75,-5],[0.006170592,-0.707079857,0.707079857,-0.006170592],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget Corn1:=[[-17.5,-2.25,-21],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget Corn2:=[[404,1.5,-18],[0.055478959,-0.704927007,0.704927007,-0.055478959],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget Corn3:=[[403.5,419.75,-12],[0.055478959,-0.704927007,0.704927007,-0.055478959],[0,-1,-1,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget Corn4:=[[-11,414.7,-19],[0,-0.707106781,0.707106781,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget C1:=[[378,129.5,-2],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget C2:=[[325.5,129.5,-2],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget C3:=[[272.5,130,-3],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget C4:=[[220.5,129,-2.5],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget C5:=[[167,128.5,-3],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget C6:=[[113.5,126.5,-3],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget C7:=[[61.5,125,-4],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget C8:=[[7,123,-2.5],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget D1:=[[377,183.5,1],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget D2:=[[324.5,183.5,-2],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget D3:=[[272,182.5,-2],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget D4:=[[219.5,182,-3],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget D5:=[[167.5,181.5,-2.5],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget D6:=[[114.5,180.5,-4],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget D7:=[[62.5,176,-5],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget D8:=[[10,176,-6],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget E5:=[[169,234,-5],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget E6:=[[115.5,231.5,-4],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget E7:=[[64,230.5,-5],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget E8:=[[12.5,228,-6],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget F1:=[[377.5,288,0],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget F2:=[[325,287,0],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget F3:=[[273,287,-2],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget F4:=[[220.5,287,-1],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget F5:=[[168.5,286,-2],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget F6:=[[116,283.5,-3.5],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget F7:=[[65,281.5,-6],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget F8:=[[15,281,-6],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget G1:=[[376.5,339.5,0],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget G2:=[[324.5,340,0],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget G3:=[[272.5,339.5,-1],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget G4:=[[221,339.5,-2.5],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget G5:=[[169,338.5,-2.5],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget G6:=[[116.5,337,-4],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget G7:=[[65,336.5,-5],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget G8:=[[16.5,335.5,-5],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget H1:=[[378,391.5,-4],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget H2:=[[326,392.5,0],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget H3:=[[273,391.5,-0.5],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget H4:=[[222,391.5,-2],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget H5:=[[169,390.5,-2],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget H6:=[[117,389.5,-2],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget H7:=[[65.5,389,-3],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget H8:=[[16,389,-3],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget A1S:=[[371,26.5,105],[0.055478959,-0.704927007,0.704927007,-0.055478959],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget A2S:=[[325.5,25.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget A3S:=[[273,25.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget A4S:=[[220.5,25.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget A5S:=[[168,24.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget A6S:=[[114.5,25,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget A7S:=[[62,24.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget A8S:=[[8,23.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget B8S:=[[6.5,75,117],[0.006170592,-0.707079857,0.707079857,-0.006170592],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget B7S:=[[62,75,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget B6S:=[[115,76,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget B5S:=[[168.5,77,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget B4S:=[[221,77.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget B3S:=[[272.5,78,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget B2S:=[[326,77.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget B1S:=[[378,78.5,105],[0.055478959,-0.704927007,0.704927007,-0.055478959],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget H7S:=[[65.5,389,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget H6S:=[[117,389.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget H5S:=[[169,390.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget H4S:=[[222,391.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget H3S:=[[273,391.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget H2S:=[[326,392.5,117],[0.006170592,-0.707079857,0.707079857,-0.006170592],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget H1S:=[[378,391.5,105],[0.067773182,-0.703851402,0.703851402,-0.067773182],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget G8S:=[[16.5,335.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget G7S:=[[65,336.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget G6S:=[[116.5,337,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget G5S:=[[169,338.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget G3S:=[[272.5,339.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget G2S:=[[324.5,340,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget G1S:=[[376.5,339.5,105],[0.055478959,-0.704927007,0.704927007,-0.055478959],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget F8S:=[[15,281,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget F7S:=[[65,281.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget F6S:=[[116,283.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget F5S:=[[168.5,286,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget F4S:=[[220.5,287,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget F3S:=[[273,287,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget F2S:=[[325,287,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget F1S:=[[377.5,288,105],[0.055478959,-0.704927007,0.704927007,-0.055478959],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget E8S:=[[12.5,228,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget E7S:=[[64,230.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget E6S:=[[115.5,231.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget E5S:=[[169,234,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget E4S:=[[220.5,234,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget E3S:=[[272.5,235,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget E2S:=[[324.5,235.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget E1S:=[[377.5,235.5,105],[0.055478959,-0.704927007,0.704927007,-0.055478959],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget D8S:=[[10,176,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget D7S:=[[62.5,176,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget D6S:=[[114.5,180.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget D5S:=[[167.5,181.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget D4S:=[[219.5,182,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget D3S:=[[272,182.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget D2S:=[[324.5,183.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget D1S:=[[377,183.5,105],[0.055478959,-0.704927007,0.704927007,-0.055478959],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget C8S:=[[7,123,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget C7S:=[[61.5,125,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget C6S:=[[113.5,126.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget C5S:=[[167,128.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget C4S:=[[220.5,129,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget C1S:=[[378,129.5,105],[0.055478959,-0.704927007,0.704927007,-0.055478959],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget G4S:=[[221,339.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget H8S:=[[16,389,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget C3S:=[[272.5,130,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    CONST robtarget C2S:=[[325.5,129.5,117],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    
    !***********************************************************
    !
    ! M?dulo:  Module1
    !
    ! Descripci n:
    !   <Introduzca la descripci n aqu >
    !
    ! Autor: Kenny Serrudo
    !
    ! Versi n: 1.0
    !
    !***********************************************************
    
    
    !***********************************************************
    !
    
    ! Procedimiento Main
    !
    !   Este es el punto de entrada de su programa
    !
    !***********************************************************

        CONST robtarget Cap1:=[[-84,441,-3],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap2:=[[-136,441,-3],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap3:=[[-188,441,-3],[0,-0.707106781,0.707106781,0],[1,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap4:=[[-240,441,-3],[0,-0.707106781,0.707106781,0],[1,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap5:=[[-292,441,-3],[0,-0.707106781,0.707106781,0],[1,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap6:=[[-84,493,-3],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap7:=[[-136,493,-3],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap8:=[[-188,493,-3],[0,-0.707106781,0.707106781,0],[1,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap9:=[[-240,493,-3],[0,-0.707106781,0.707106781,0],[1,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap10:=[[-292,493,-3],[0,-0.707106781,0.707106781,0],[1,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap11:=[[-84,545,-3],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap12:=[[-136,545,-3],[0,-0.707106781,0.707106781,0],[-1,0,-2,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap13:=[[-188,545,-3],[0,-0.707106781,0.707106781,0],[1,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap14:=[[-240,545,-3],[0,-0.707106781,0.707106781,0],[1,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap15:=[[-292,545,-3],[0,-0.707106781,0.707106781,0],[1,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap15S:=[[-292,545,117],[0,-0.707106781,0.707106781,0],[1,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap14S:=[[-240,545,117],[0,-0.707106781,0.707106781,0],[1,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap13S:=[[-188,545,117],[0,-0.707106781,0.707106781,0],[1,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap12S:=[[-136,545,117],[0,-0.707106781,0.707106781,0],[0,0,-1,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap11S:=[[-84,545,117],[0,-0.707106781,0.707106781,0],[0,0,-1,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap10S:=[[-292,493,117],[0,-0.707106781,0.707106781,0],[1,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap9S:=[[-240,493,117],[0,-0.707106781,0.707106781,0],[1,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap8S:=[[-188,493,117],[0,-0.707106781,0.707106781,0],[1,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap7S:=[[-136,493,117],[0,-0.707106781,0.707106781,0],[0,0,-1,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap6S:=[[-84,493,117],[0,-0.707106781,0.707106781,0],[0,0,-1,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap5S:=[[-292,441,117],[0,-0.707106781,0.707106781,0],[1,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap4S:=[[-240,441,117],[0,-0.707106781,0.707106781,0],[1,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap3S:=[[-188,441,117],[0,-0.707106781,0.707106781,0],[1,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap2S:=[[-136,441,117],[0,-0.707106781,0.707106781,0],[0,0,-1,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        CONST robtarget Cap1S:=[[-84,441,117],[0,-0.707106781,0.707106781,0],[0,0,-1,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        
        VAR bool Pinza:=true;
        ! ====== VARIABLES DE SOCKET ======
        VAR socketdev pc_socket;
        VAR string recv_str;
        VAR num cambio;
        VAR num casilla_recv;
        ! ====== TIEMPOS DE PINZA ======
        VAR num Tiempo1Grip := 1;
        VAR num Tiempo2Grip := 1;

        VAR bool check_convert;
        VAR string msg;
        VAR bool primeraCasilla := TRUE;
        VAR num casilla_origen;
        VAR bool enroqueDetectado := FALSE;
        
        VAR num habienroque := 1;
    PROC main()
        InitSquares;
        SocketCreate pc_socket;
        
        SocketConnect pc_socket, "192.168.125.203", 5000;
        TPWrite "Conectado a PC";
        MoveL PSegHome, v200, fine, Gripper1\WObj:=wobj0;
        SetDO DO1, 1;   ! verde OFF
        SetDO DO3, 0; 
        
        WHILE TRUE DO
            ! Leer mensaje como string (bloqueante)
            SocketReceive pc_socket \Str:=recv_str \Time:=1200;
            msg:= "Recibido: "+ recv_str;
            TPWrite msg;
            SetDO DO1, 0;   ! verde OFF
            SetDO DO3, 1;   ! azul ON
            check_convert:=StrToVal(recv_str,casilla_recv);
            
            ! =======================
            ! ORIGEN / DESTINO
            ! =======================
            IF primeraCasilla THEN
                
                ! -------- ORIGEN --------
                casilla_origen := casilla_recv;
                MoveL PSegCenter, v200, fine, Gripper1\WObj:=Workobject_1;
                MoveSquare Squares{casilla_recv}.safe, Squares{casilla_recv}.final, Pinza;
                Pinza := NOT Pinza;
                primeraCasilla := FALSE;
            ELSE
                ! -------- DESTINO --------
                MoveL PSegCenter, v200, fine, Gripper1\WObj:=Workobject_1;
                MoveSquare Squares{casilla_recv}.safe, Squares{casilla_recv}.final, Pinza;
                Pinza := NOT Pinza;
    
                ! ---------- ENROQUES ----------
                ! Rey negro E8 = 40
                ! G8 = 56, C8 = 24
                IF casilla_origen = 40 AND casilla_recv = 56 THEN
                    TPWrite "Enroque corto detectado. Torre H8 -> F8";
                    MoveSquare Squares{64}.safe, Squares{64}.final, TRUE;   ! H8
                    MoveSquare Squares{48}.safe, Squares{48}.final, FALSE;  ! F8
    
                ELSEIF casilla_origen = 40 AND casilla_recv = 24 THEN
                    TPWrite "Enroque largo detectado. Torre A8 -> D8";
                    MoveSquare Squares{8}.safe, Squares{8}.final, TRUE;     ! A8
                    MoveSquare Squares{32}.safe, Squares{32}.final, FALSE;  ! D8
                ENDIF
                ! Después de la segunda casilla (normal o enroque) ? Home
                MoveL PSegHome, v200, fine, Gripper1\WObj:=wobj0;
                WaitTime 8;   ! cambio
                SetDO DO3, 0;   ! azul OFF
                SetDO DO1, 1;   ! verde ON
                primeraCasilla := TRUE;
            ENDIF
        ENDWHILE

    ERROR
        TPWrite "Error de socket, cerrando.";
        SocketClose pc_socket;
        WHILE TRUE DO
            SetDO DO1, 1;
            SetDO DO3, 0;
            WaitTime 0.5;
            SetDO DO1, 0;
            SetDO DO3, 1;
            WaitTime 0.5;
        ENDWHILE
        
    ENDPROC    
    
    PROC MoveSquare(robtarget safePoint, robtarget finalPoint, bool grip)
        MoveL safePoint, v150, fine, Gripper1\WObj:=Workobject_1;
        MoveL finalPoint, v150, fine, Gripper1\WObj:=Workobject_1;
        
        WaitTime Tiempo1Grip;
        IF grip=TRUE THEN
            SetDO DO2, 1;
        ELSE
            SetDO DO2, 0;
        ENDIF
        WaitTime Tiempo2Grip;
        MoveL safePoint, v150, fine, Gripper1\WObj:=Workobject_1;
        MoveL PSegCenter, v150, fine, Gripper1\WObj:=Workobject_1;
    ENDPROC
    !Funcion de inicializacion
    PROC InitSquares()
    
        ! --- Columna A ---
        Squares{1}.safe := A1S;    Squares{1}.final := A1;
        Squares{2}.safe := A2S;    Squares{2}.final := A2;
        Squares{3}.safe := A3S;    Squares{3}.final := A3;
        Squares{4}.safe := A4S;    Squares{4}.final := A4;
        Squares{5}.safe := A5S;    Squares{5}.final := A5;
        Squares{6}.safe := A6S;    Squares{6}.final := A6;
        Squares{7}.safe := A7S;    Squares{7}.final := A7;
        Squares{8}.safe := A8S;    Squares{8}.final := A8;
    
        ! --- Columna B ---
        Squares{9}.safe  := B1S;   Squares{9}.final  := B1;
        Squares{10}.safe := B2S;   Squares{10}.final := B2;
        Squares{11}.safe := B3S;   Squares{11}.final := B3;
        Squares{12}.safe := B4S;   Squares{12}.final := B4;
        Squares{13}.safe := B5S;   Squares{13}.final := B5;
        Squares{14}.safe := B6S;   Squares{14}.final := B6;
        Squares{15}.safe := B7S;   Squares{15}.final := B7;
        Squares{16}.safe := B8S;   Squares{16}.final := B8;
    
        ! --- Columna C ---
        Squares{17}.safe := C1S;   Squares{17}.final := C1;
        Squares{18}.safe := C2S;   Squares{18}.final := C2;
        Squares{19}.safe := C3S;   Squares{19}.final := C3;
        Squares{20}.safe := C4S;   Squares{20}.final := C4;
        Squares{21}.safe := C5S;   Squares{21}.final := C5;
        Squares{22}.safe := C6S;   Squares{22}.final := C6;
        Squares{23}.safe := C7S;   Squares{23}.final := C7;
        Squares{24}.safe := C8S;   Squares{24}.final := C8;
    
        ! --- Columna D ---
        Squares{25}.safe := D1S;   Squares{25}.final := D1;
        Squares{26}.safe := D2S;   Squares{26}.final := D2;
        Squares{27}.safe := D3S;   Squares{27}.final := D3;
        Squares{28}.safe := D4S;   Squares{28}.final := D4;
        Squares{29}.safe := D5S;   Squares{29}.final := D5;
        Squares{30}.safe := D6S;   Squares{30}.final := D6;
        Squares{31}.safe := D7S;   Squares{31}.final := D7;
        Squares{32}.safe := D8S;   Squares{32}.final := D8;
    
        ! --- Columna E ---
        Squares{33}.safe := E1S;   Squares{33}.final := E1;
        Squares{34}.safe := E2S;   Squares{34}.final := E2;
        Squares{35}.safe := E3S;   Squares{35}.final := E3;
        Squares{36}.safe := E4S;   Squares{36}.final := E4;
        Squares{37}.safe := E5S;   Squares{37}.final := E5;
        Squares{38}.safe := E6S;   Squares{38}.final := E6;
        Squares{39}.safe := E7S;   Squares{39}.final := E7;
        Squares{40}.safe := E8S;   Squares{40}.final := E8;
    
        ! --- Columna F ---
        Squares{41}.safe := F1S;   Squares{41}.final := F1;
        Squares{42}.safe := F2S;   Squares{42}.final := F2;
        Squares{43}.safe := F3S;   Squares{43}.final := F3;
        Squares{44}.safe := F4S;   Squares{44}.final := F4;
        Squares{45}.safe := F5S;   Squares{45}.final := F5;
        Squares{46}.safe := F6S;   Squares{46}.final := F6;
        Squares{47}.safe := F7S;   Squares{47}.final := F7;
        Squares{48}.safe := F8S;   Squares{48}.final := F8;
    
        ! --- Columna G ---
        Squares{49}.safe := G1S;   Squares{49}.final := G1;
        Squares{50}.safe := G2S;   Squares{50}.final := G2;
        Squares{51}.safe := G3S;   Squares{51}.final := G3;
        Squares{52}.safe := G4S;   Squares{52}.final := G4;
        Squares{53}.safe := G5S;   Squares{53}.final := G5;
        Squares{54}.safe := G6S;   Squares{54}.final := G6;
        Squares{55}.safe := G7S;   Squares{55}.final := G7;
        Squares{56}.safe := G8S;   Squares{56}.final := G8;
    
        ! --- Columna H ---
        Squares{57}.safe := H1S;   Squares{57}.final := H1;
        Squares{58}.safe := H2S;   Squares{58}.final := H2;
        Squares{59}.safe := H3S;   Squares{59}.final := H3;
        Squares{60}.safe := H4S;   Squares{60}.final := H4;
        Squares{61}.safe := H5S;   Squares{61}.final := H5;
        Squares{62}.safe := H6S;   Squares{62}.final := H6;
        Squares{63}.safe := H7S;   Squares{63}.final := H7;
        Squares{64}.safe := H8S;   Squares{64}.final := H8;
        
        ! --- Columna De Capturas ---
        Squares{65}.safe := Cap1S;   Squares{65}.final := Cap1;
        Squares{66}.safe := Cap2S;   Squares{66}.final := Cap2;
        Squares{67}.safe := Cap3S;   Squares{67}.final := Cap3;
        Squares{68}.safe := Cap4S;   Squares{68}.final := Cap4;
        Squares{69}.safe := Cap5S;   Squares{69}.final := Cap5;
        Squares{70}.safe := Cap6S;   Squares{70}.final := Cap6;
        Squares{71}.safe := Cap7S;   Squares{71}.final := Cap7;
        Squares{72}.safe := Cap8S;   Squares{72}.final := Cap8;
        Squares{73}.safe := Cap9S;   Squares{73}.final := Cap9;
        Squares{74}.safe := Cap10S;   Squares{74}.final := Cap10;
        Squares{75}.safe := Cap11S;   Squares{75}.final := Cap11;
        Squares{76}.safe := Cap12S;   Squares{76}.final := Cap12;
        Squares{77}.safe := Cap13S;   Squares{77}.final := Cap13;
        Squares{78}.safe := Cap14S;   Squares{78}.final := Cap14;
        Squares{79}.safe := Cap15S;   Squares{79}.final := Cap15;
    ENDPROC
    PROC Path_20()
        MoveL Cap1,v150,fine,Gripper1\WObj:=Workobject_1;
    ENDPROC
    PROC Path_30()
        MoveL D6S,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap1,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap2,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap3,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap4,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap5,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap6,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap7,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap8,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap9,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap10,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap11,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap12,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap13,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap14,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap15,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap15S,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap15,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap14S,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap14,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap13S,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap13,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap12S,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap12,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap11S,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap11,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap10S,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap10,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap9S,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap9,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap8S,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap8,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap7S,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap7,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap6S,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap6,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap5S,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap5,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap4S,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap4,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap3S,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap3,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap2S,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap2,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap1S,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL Cap1,v150,fine,Gripper1\WObj:=Workobject_1;
        MoveL D6S,v150,fine,Gripper1\WObj:=Workobject_1;
    ENDPROC

ENDMODULE