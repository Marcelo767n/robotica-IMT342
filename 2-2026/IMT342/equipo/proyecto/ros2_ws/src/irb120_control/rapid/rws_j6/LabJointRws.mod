MODULE LabJointRws
    ! CANDIDATO J6: verificar programa en RW6.12 antes del primer movimiento.
    ! Conserva el programa Module1 existente. No contiene main ni arranque automatico.
    CONST jointtarget noTarget := [[9E9,9E9,9E9,9E9,9E9,9E9],[9E9,9E9,9E9,9E9,9E9,9E9]];
    ! PC prepara como maximo 0.1 grados; 0.01 adicional para lectura/redondeo.
    CONST num maxDeltaDeg := 0.11;
    CONST num maxOtherDriftDeg := 0.02;
    ! [TCP mm/s, orientacion grados/s, externo lineal mm/s, externo rotativo grados/s].
    ! v5 NO limita la orientacion a 5 grados/s. Se declara explicitamente 0.5.
    CONST speeddata vLabJ6 := [5,0.5,5,0.5];
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
            TPWrite "Objetivo J6 ausente o postura fuera de ventana.";
            RETURN;
        ENDIF

        MostrarEjes objetivo.robax;
        TPReadFK respuesta,"Solo J6. Ejecutar objetivo?",stEmpty,stEmpty,stEmpty,"Mover","Cancelar"\MaxTime:=15\BreakFlag:=motivo;
        IF motivo <> 0 OR respuesta <> 4 THEN
            RETURN;
        ENDIF

        actual := CJointT();
        IF OpMode() <> OP_MAN_PROG OR ObjetivoCercano(objetivo.robax, actual.robax) = FALSE THEN
            TPWrite "Cambio de modo o posicion. Prueba cancelada.";
            RETURN;
        ENDIF

        ! La unica componente sustituida es J6. Las otras cinco y los externos
        ! proceden del CJointT inmediatamente anterior al MoveAbsJ.
        actual.robax.rax_6 := objetivo.robax.rax_6;
        MoveAbsJ actual,vLabJ6,fine,tool0;
        TPWrite "Movimiento J6 terminado.";
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
        RETURN Abs(destino.rax_1 - actual.rax_1) <= maxOtherDriftDeg AND
               Abs(destino.rax_2 - actual.rax_2) <= maxOtherDriftDeg AND
               Abs(destino.rax_3 - actual.rax_3) <= maxOtherDriftDeg AND
               Abs(destino.rax_4 - actual.rax_4) <= maxOtherDriftDeg AND
               Abs(destino.rax_5 - actual.rax_5) <= maxOtherDriftDeg AND
               Abs(destino.rax_6 - actual.rax_6) <= maxDeltaDeg AND
               destino.rax_6 >= -398 AND destino.rax_6 <= 398;
    ENDFUNC
ENDMODULE
