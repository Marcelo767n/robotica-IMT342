MODULE IRB120_EGM_Prueba
    ! PLANTILLA PARA REVISION EN ROBOTSTUDIO / RW6.12.
    ! No compilada ni ejecutada en el controlador fisico por este proyecto.
    ! No instala UDPUC, no enciende motores y no contiene MoveAbsJ automatico.
    ! El operador debe cumplir las condiciones previas/fine point de ABB.
    PERS bool revisionLaboratorioCompletada:=FALSE;
    VAR egmident egmId;
    VAR num respuesta;
    CONST egm_minmax llegada:=[-0.02,0.02];

    PROC main()
        IF NOT revisionLaboratorioCompletada THEN
            TPWrite "NO-GO: revisar modulo, respaldo, red, TCP, limites y parada.";
            RETURN;
        ENDIF
        EGMGetId egmId;
        ! PC_IRB120 y default deben coincidir con la configuracion REVISADA.
        EGMSetupUC ROB_1,egmId,"default","PC_IRB120"\Joint\CommTimeout:=0.1;
        ! 8 ms / 2 grados son valores propuestos para la estacion virtual.
        ! Deben concordar con la ficha de sesion que se apruebe para hardware.
        EGMActJoint egmId\StreamStart\Tool:=tool0\WObj:=wobj0
            \J1:=llegada\J2:=llegada\J3:=llegada
            \J4:=llegada\J5:=llegada\J6:=llegada
            \SampleRate:=8\MaxPosDeviation:=2\MaxSpeedDeviation:=0.5;
        ! Stream primero: PC recibe estado y ARMA mantenimiento desde RViz.
        ! Revisar que este dialogo conserve RAPID_RUNNING en el controlador concreto.
        TPReadFK respuesta,"PC en ARMADO y postura verificada?","Continuar","","","","Salir";
        IF respuesta<>1 THEN
            EGMReset egmId;
            RETURN;
        ENDIF
        ! CondTime es tiempo de convergencia, NO limite total de sesion.
        ! La PC limita la sesion; CommTimeout debe parar ante ausencia de paquetes.
        EGMRunJoint egmId,EGM_STOP_HOLD\J1\J2\J3\J4\J5\J6
            \CondTime:=120\RampInTime:=0.2\RampOutTime:=0.2;
        EGMReset egmId;
    ERROR
        ! No hay RETRY ni reinicio automatico tras fallo de comunicacion.
        TPWrite "EGM detenido por error. Revisar antes de otra prueba.";
        RAISE;
    ENDPROC
ENDMODULE
