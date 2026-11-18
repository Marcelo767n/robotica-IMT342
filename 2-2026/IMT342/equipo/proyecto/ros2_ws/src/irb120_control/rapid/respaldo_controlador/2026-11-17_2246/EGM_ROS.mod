MODULE EGM_ROS
    !==================================================================================
    ! EGM joint-position module for ROS 2 (abb_ros2 / abb_hardware_interface)
    ! Robot: IRB 120-3/0.6 - IRC5 Compact - RobotWare 6.12.01
    !
    ! Adapted from abb_ros2/robot_studio_resources/TRob1Main.mod
    ! (Copyright (c) 2018, ABB Schweiz AG - BSD-3-Clause)
    !
    ! Differences from the original:
    !   * NO "PROC main": the existing Module1 (production program) keeps its main.
    !     Start this with FlexPendant -> Debug -> "PP to Routine..." -> ros_egm
    !   * NO automatic MoveAbsJ to home: the robot does not move on start.
    !     Jog it to a safe position by hand before starting.
    !   * MaxSpeedDeviation lowered from 20 to 10 deg/s for the first tests.
    !
    ! Requires: UDPUC device "ROB_1" -> Remote Address 192.168.125.10, port 6511
    !           (Configuration -> Communication -> Transmission Protocol)
    !==================================================================================

    ! EGM identifier.
    LOCAL VAR egmident egm_id;

    ! Convergence condition [deg] (same as the original).
    LOCAL VAR egm_minmax egm_condition := [-0.1, 0.1];

    ! Maximum speed deviation allowed from EGM [deg/s].
    ! Raise it (original: 20) only once everything works.
    LOCAL CONST num max_speed_dev := 10;

    PROC ros_egm()
        VAR jointtarget inicio_egm;
        TPWrite "EGM_ROS: waiting for ROS 2 (UDP ROB_1 -> 192.168.125.10:6511)";
        
        inicio_egm := CJointT();
        MoveAbsJ inicio_egm, v10, fine, tool0;

        ! Register an EGM id.
        EGMGetId egm_id;

        ! Joint-mode EGM over the UDPUC device ROB_1, with the "default" MOC profile.
        EGMSetupUC ROB_1, egm_id, "default", "ROB_1", \Joint;

        ! Prepare the EGM session.
        EGMActJoint egm_id
                    \J1:=egm_condition
                    \J2:=egm_condition
                    \J3:=egm_condition
                    \J4:=egm_condition
                    \J5:=egm_condition
                    \J6:=egm_condition
                    \MaxSpeedDeviation:=max_speed_dev;

        WHILE TRUE DO
            ! Run EGM: the robot follows the positions sent by ROS 2.
            EGMRunJoint egm_id, EGM_STOP_HOLD, \J1 \J2 \J3 \J4 \J5 \J6 \CondTime:=5 \RampOutTime:=5;
        ENDWHILE

    ERROR
        IF ERRNO = ERR_UDPUC_COMM THEN
            ! ROS 2 is not sending data (timeout): keep waiting.
            TPWrite "EGM_ROS: communication timeout, retrying";
            TRYNEXT;
        ENDIF
    ENDPROC

    ! Run this (PP to Routine -> ros_egm_reset) if a previous session was
    ! aborted and EGMGetId/EGMSetupUC complains that the id is in use.
    PROC ros_egm_reset()
        EGMReset egm_id;
        TPWrite "EGM_ROS: egm_id released";
    ENDPROC
    
        PROC ros_egm_verificar()
        EGMGetId egm_id;
        EGMSetupUC ROB_1, egm_id, "default", "ROB_1"\Joint;

        TPWrite "Enviando posiciones EGM durante 20 segundos";
        EGMStreamStart egm_id;
        WaitTime 20;
        EGMStreamStop egm_id;

        EGMReset egm_id;
        TPWrite "Prueba EGM terminada";
    ENDPROC
ENDMODULE
