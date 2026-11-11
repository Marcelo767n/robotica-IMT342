MODULE LabJointRws
    CONST jointtarget noTarget := [[9E9,9E9,9E9,9E9,9E9,9E9],[9E9,9E9,9E9,9E9,9E9,9E9]];
    CONST num maxDeltaDeg := 1;
    PERS jointtarget pcTarget := [[9E9,9E9,9E9,9E9,9E9,9E9],[9E9,9E9,9E9,9E9,9E9,9E9]];

    PROC MostrarObjetivo()
        MostrarEjes pcTarget.robax;
    ENDPROC

    PROC ProbarObjetivo()
        VAR jointtarget objetivo;
        VAR jointtarget actual;
        VAR num respuesta := 0;
        VAR errnum motivo := 0;

        IF OpMode() <> OP_MAN_PROG THEN
            TPWrite "Seleccione modo manual reducido.";
            RETURN;
        ENDIF

        objetivo := pcTarget;
        pcTarget := noTarget;
        actual := CJointT();
        IF NOT ObjetivoCercano(objetivo.robax, actual.robax) THEN
            TPWrite "Sin objetivo o diferencia mayor a 1 grado.";
            RETURN;
        ENDIF

        MostrarEjes objetivo.robax;
        TPReadFK respuesta,"Ejecutar el objetivo mostrado?",stEmpty,stEmpty,stEmpty,"Mover","Cancelar"\MaxTime:=15\BreakFlag:=motivo;
        IF motivo <> 0 OR respuesta <> 4 THEN
            RETURN;
        ENDIF

        actual := CJointT();
        IF OpMode() <> OP_MAN_PROG OR ObjetivoCercano(objetivo.robax, actual.robax) = FALSE THEN
            TPWrite "Cambio de modo o de posicion. Prueba cancelada.";
            RETURN;
        ENDIF

        objetivo.extax := actual.extax;
        MoveAbsJ objetivo,v5,fine,tool0;
        TPWrite "Movimiento terminado.";
    ENDPROC

    LOCAL PROC MostrarEjes(robjoint ejes)
        TPWrite "Objetivo absoluto en grados:";
        TPWrite "J1"\Num:=ejes.rax_1;
        TPWrite "J2"\Num:=ejes.rax_2;
        TPWrite "J3"\Num:=ejes.rax_3;
        TPWrite "J4"\Num:=ejes.rax_4;
        TPWrite "J5"\Num:=ejes.rax_5;
        TPWrite "J6"\Num:=ejes.rax_6;
    ENDPROC

    LOCAL FUNC bool ObjetivoCercano(robjoint destino, robjoint actual)
        RETURN Abs(destino.rax_1 - actual.rax_1) <= maxDeltaDeg AND
               Abs(destino.rax_2 - actual.rax_2) <= maxDeltaDeg AND
               Abs(destino.rax_3 - actual.rax_3) <= maxDeltaDeg AND
               Abs(destino.rax_4 - actual.rax_4) <= maxDeltaDeg AND
               Abs(destino.rax_5 - actual.rax_5) <= maxDeltaDeg AND
               Abs(destino.rax_6 - actual.rax_6) <= maxDeltaDeg;
    ENDFUNC
ENDMODULE

