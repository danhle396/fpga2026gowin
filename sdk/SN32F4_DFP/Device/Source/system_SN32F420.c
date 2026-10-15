/******************************************************************************
 * @file     system_SN32F420.c
 * @brief    CMSIS Cortex-M0 Device Peripheral Access Layer Source File
 *           for the SONIX SN32F420 Devices
 * @version  V1.0.6
 * @date     2026/05/20
 *
 * @note
 * Copyright (C) 2022-2026 ARM Limited. All rights reserved.
 *
 * @par
 * ARM Limited (ARM) is supplying this software for use with Cortex-M 
 * processor based microcontrollers.  This file can be freely distributed 
 * within development tools that are supporting such ARM based processors. 
 *
 * @par
 * THIS SOFTWARE IS PROVIDED "AS IS".  NO WARRANTIES, WHETHER EXPRESS, IMPLIED
 * OR STATUTORY, INCLUDING, BUT NOT LIMITED TO, IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE APPLY TO THIS SOFTWARE.
 * ARM SHALL NOT, IN ANY CIRCUMSTANCES, BE LIABLE FOR SPECIAL, INCIDENTAL, OR
 * CONSEQUENTIAL DAMAGES, FOR ANY REASON WHATSOEVER.
 *
 ******************************************************************************/


#include <stdint.h>
#include <SN32F420.h>



/*
//-------- <<< Use Configuration Wizard in Context Menu >>> ------------------
*/

/*--------------------- Clock Configuration ----------------------------------
//
//		<o0.0..2>  SYSCLKSEL (SYS0_CLKCFG)
//					<0=> IHRC 12M
//					<1=> ILRC
//					<4=> PLL
//	
//
//		<o1> PLL ENABLE
//					<0=> Disable
//					<1=> Enable
//		<o2>  AHB Clock Prescaler Register  (SYS0_AHBCP)
//					<0=> SYSCLK/1
//					<1=> SYSCLK/2
//					<2=> SYSCLK/4
//					<3=> SYSCLK/8
//					<4=> SYSCLK/16
//					<5=> SYSCLK/32
//					<6=> SYSCLK/64
//					<7=> SYSCLK/128
//		<o3>  SYSCLK prescaler Register  (SYS0_AHBCP)
//					<0=> SYSCLK/1
//					<1=> SYSCLK/1.5
//		<o4>  CLKOUT selection
//					<0=> Disable
//					<1=> ILRC
//					<4=> HCLK
//					<5=> IHRC
//					<7=> PLL
//		<o5> CLKOUT Prescaler Register  (SYS1_APBCP1)
//					<0=> CLKOUT selection/1
//					<1=> CLKOUT selection/2
//					<2=> CLKOUT selection/4
//					<3=> CLKOUT selection/8
//					<4=> CLKOUT selection/16
//					<5=> CLKOUT selection/32
//					<6=> CLKOUT selection/64
//					<7=> CLKOUT selection/128
*/


#define SYS0_CLKCFG_VAL		0
#define PLL_ENABLE			0
#define AHB_PRESCALAR 		0x0
#define AHB_1P5PRESCALAR 	0x0
#define CLKOUT_SEL_VAL 		0x0
#define CLKOUT_PRESCALAR 	0x0

/*
//-------- <<< end of configuration section >>> ------------------------------
*/


/*----------------------------------------------------------------------------
  DEFINES
 *----------------------------------------------------------------------------*/
#define	IHRC			0
#define	ILRC			1
#define PLL				4

/*----------------------------------------------------------------------------
  Define clocks
 *----------------------------------------------------------------------------*/
#define __IHRC_FREQ			(12000000UL)
#define __ILRC_FREQ			(32000UL)
#define __PLL_FREQ			(48000000UL)


#define SYS0_PLLCTRL_VAL	(PLL_ENABLE<<15)


/*----------------------------------------------------------------------------
  Clock Variable definitions
 *----------------------------------------------------------------------------*/
uint32_t SystemCoreClock;	/*!< System Clock Frequency (Core Clock)*/


/*----------------------------------------------------------------------------
  Clock functions
 *----------------------------------------------------------------------------*/
void SystemCoreClockUpdate (void)            /* Get Core Clock Frequency      */
{
	uint32_t AHB_prescaler;

	switch (SN_SYS0->CLKCFG_b.SYSCLKST)
	{
		case 0:		//IHRC
			SystemCoreClock = __IHRC_FREQ;
			break;
		case 1:		//ILRC
			SystemCoreClock = __ILRC_FREQ;
			break;
		case 4: 	//PLL
			SystemCoreClock = __PLL_FREQ;
			break;
		default:
			break;
	}

	switch (SN_SYS0->AHBCP_b.AHBPRE)
	{
		case 0:	AHB_prescaler = 1;	break;
		case 1:	AHB_prescaler = 2;	break;
		case 2:	AHB_prescaler = 4;	break;
		case 3:	AHB_prescaler = 8;	break;
		case 4:	AHB_prescaler = 16;	break;
		case 5:	AHB_prescaler = 32;	break;
		case 6:	AHB_prescaler = 64;	break;
		case 7:	AHB_prescaler = 128;break;
		default: break;	
	}

	SystemCoreClock /= AHB_prescaler;
	
	if (SN_SYS0->AHBCP_b.DIV1P5 == 1)
		SystemCoreClock = SystemCoreClock*2/3;

	//;;;;;;;;; Need for SN32F420 Begin	;;;;;;;;;
	if (SystemCoreClock > 24000000)
		SN_FLASH->LPCTRL = 0x5AFA0011;
	else
		SN_FLASH->LPCTRL = 0x5AFA0000;
	//;;;;;;;;; Need for SN32F420 End	;;;;;;;;;

	return;
}

/**
 * Initialize the system
 *
 * @param  none
 * @return none
 *
 * @brief  Setup the microcontroller system.
 *         Initialize the System.
 */
void SystemInit (void)
{
	#if (SYS0_CLKCFG_VAL == IHRC)			//IHRC
	SN_SYS0->CLKCFG = 0x0;
	while ((SN_SYS0->CLKCFG & 0x70) != 0x0);
	#endif

	#if (SYS0_CLKCFG_VAL == ILRC)			//ILRC
	SN_SYS0->CLKCFG = 0x1;
	while ((SN_SYS0->CLKCFG & 0x70) != 0x10);
	#endif

	#if (PLL_ENABLE == 1)
	SN_SYS0->PLLCTRL = SYS0_PLLCTRL_VAL;

	while ((SN_SYS0->CSST & 0x40) != 0x40);
	#if (SYS0_CLKCFG_VAL == PLL)			//PLL
	SN_FLASH->LPCTRL = 0x5AFA0011;			//48MHz
	SN_SYS0->CLKCFG = 0x4;
	while ((SN_SYS0->CLKCFG & 0x70) != 0x40);
	#endif
	#endif
	
	SN_SYS0->AHBCP = AHB_PRESCALAR;
	SN_SYS0->AHBCP_b.DIV1P5 = AHB_1P5PRESCALAR;

	#if (CLKOUT_SEL_VAL > 0)			//CLKOUT
	SN_SYS1->AHBCLKEN_b.CLKOUTSEL = CLKOUT_SEL_VAL;
	SN_SYS1->APBCP1_b.CLKOUTPRE = CLKOUT_PRESCALAR;
	#endif
	

}
