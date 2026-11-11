MODULE LabJointRws
    ! V2 SERVIDOR PC. Recibe objetivos articulares absolutos (grados, J1..J6)
    ! escritos por RWS desde Linux (rws_mover.py) y los ejecuta con MoveAbsJ.
    ! No tiene main ni arranque automatico: el operador selecciona ServidorPC con
    ! PP to Routine, en manual reducido, y lo arranca con habilitador + Start.
    !
    ! Protocolo: la PC escribe pcTarget, lo lee de vuelta y DESPUES incrementa
    ! pcSeq. El robot valida, mueve y responde: primero rbCodigo, luego rbSeq.
    ! rbCodigo: 0 listo, 1 moviendo, 2 llegada,
    !          -1 objetivo vacio o no valido, -2 fuera de limites con margen,
    !          -3 algun eje cambia mas de maxPasoDeg, -4 modo no permitido.
    CONST num maxPasoDeg := 10;
    CONST num margenDeg := 2;
    ! Plan B en AUTO: solo con autorizacion del responsable cambiar a TRUE.
    CONST bool permitirAuto := FALSE;
    ! [TCP mm/s, orientacion grados/s, externo lineal mm/s, externo rotativo grados/s]
    CONST speeddata vPc := [20,5,20,5];
    PERS jointtarget pcTarget := [[9E9,9E9,9E9,9E9,9E9,9E9],[9E9,9E9,9E9,9E9,9E9,9E9]];
    PERS num pcSeq := 0;
    PERS num pcFin := 0;
    PERS num rbSeq := 0;
    PERS num rbCodigo := 0;
    PERS num rbActivo := 0;

    PROC MostrarObjetivo()
        MostrarEjes pcTarget.robax;
    ENDPROC

    PROC ServidorPC()
        VAR jointtarget objetivo;
        VAR jointtarget actual;
        VAR num seq := 0;
        VAR num respuesta := 0;
        VAR errnum motivo := 0;

        rbActivo := 0;
        IF ModoPermitido() = FALSE THEN
            TPWrite "Seleccione manual reducido.";
            RETURN;
        ENDIF
        TPReadFK respuesta,"Aceptar objetivos enviados por la PC?",stEmpty,stEmpty,stEmpty,"Iniciar","Cancelar"\MaxTime:=30\BreakFlag:=motivo;
        IF motivo <> 0 OR respuesta <> 4 THEN
            TPWrite "Servidor PC cancelado.";
            RETURN;
        ENDIF
        ! Ignorar cualquier orden escrita antes del arranque.
        pcFin := 0;
        rbCodigo := 0;
        rbSeq := pcSeq;
        rbActivo := 1;
        TPWrite "Servidor PC activo. Esperando objetivos.";
        WHILE pcFin = 0 DO
            IF pcSeq <> rbSeq THEN
                seq := pcSeq;
                objetivo := pcTarget;
                actual := CJointT();
                rbCodigo := Validar(objetivo.robax, actual.robax);
                IF rbCodigo = 0 THEN
                    rbCodigo := 1;
                    TPWrite "Moviendo orden"\Num:=seq;
                    objetivo.extax := actual.extax;
                    MoveAbsJ objetivo,vPc,fine,tool0;
                    rbCodigo := 2;
                ELSE
                    TPWrite "Orden rechazada, codigo"\Num:=rbCodigo;
                ENDIF
                rbSeq := seq;
            ENDIF
            WaitTime 0.1;
        ENDWHILE
        rbActivo := 0;
        TPWrite "Servidor PC terminado.";
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

    LOCAL FUNC bool ModoPermitido()
        VAR bool permitido := FALSE;
        IF OpMode() = OP_MAN_PROG THEN
            permitido := TRUE;
        ELSEIF permitirAuto THEN
            IF OpMode() = OP_AUTO THEN
                permitido := TRUE;
            ENDIF
        ENDIF
        RETURN permitido;
    ENDFUNC

    LOCAL FUNC num Validar(robjoint q, robjoint actual)
        IF ModoPermitido() = FALSE THEN
            RETURN -4;
        ENDIF
        IF Abs(q.rax_1) > 1000 OR Abs(q.rax_2) > 1000 OR Abs(q.rax_3) > 1000 OR
           Abs(q.rax_4) > 1000 OR Abs(q.rax_5) > 1000 OR Abs(q.rax_6) > 1000 THEN
            RETURN -1;
        ENDIF
        IF q.rax_1 < (-165 + margenDeg) OR q.rax_1 > (165 - margenDeg) OR
           q.rax_2 < (-110 + margenDeg) OR q.rax_2 > (110 - margenDeg) OR
           q.rax_3 < (-110 + margenDeg) OR q.rax_3 > (70 - margenDeg) OR
           q.rax_4 < (-160 + margenDeg) OR q.rax_4 > (160 - margenDeg) OR
           q.rax_5 < (-120 + margenDeg) OR q.rax_5 > (120 - margenDeg) OR
           q.rax_6 < (-400 + margenDeg) OR q.rax_6 > (400 - margenDeg) THEN
            RETURN -2;
        ENDIF
        IF Abs(q.rax_1 - actual.rax_1) > maxPasoDeg OR Abs(q.rax_2 - actual.rax_2) > maxPasoDeg OR
           Abs(q.rax_3 - actual.rax_3) > maxPasoDeg OR Abs(q.rax_4 - actual.rax_4) > maxPasoDeg OR
           Abs(q.rax_5 - actual.rax_5) > maxPasoDeg OR Abs(q.rax_6 - actual.rax_6) > maxPasoDeg THEN
            RETURN -3;
        ENDIF
        RETURN 0;
    ENDFUNC
ENDMODULE
