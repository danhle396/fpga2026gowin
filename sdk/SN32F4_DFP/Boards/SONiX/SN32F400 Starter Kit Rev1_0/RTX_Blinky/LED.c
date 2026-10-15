/*-----------------------------------------------------------------------------
 * Name:    LED.c
 * Purpose: Low level LED functions
 *-----------------------------------------------------------------------------
 * This file is part of the uVision/ARM development tools.
 * This software may only be used under the terms of a valid, current,
 * end user licence from KEIL for a compatible version of KEIL software
 * development tools. Nothing else gives you the right to use this software.
 *
 * This software is supplied "AS IS" without warranties of any kind.
 *
 * Copyright (c) 2004-2013 KEIL - An ARM Company. All rights reserved.
 *----------------------------------------------------------------------------*/

#include "SN32F400.h"                   // Device header
#include "led.h"


void LED_Initialize(void)
{
	SN_GPIO2->MODE = 0x3FF;			//Set P2 as output
}

void LED_On(int led)
{
  led &= 0x02;
	SN_GPIO2->DATA = (1<<led);		// P2.1
}

void LED_Off(int led)
{
  led &= 0x02;
	SN_GPIO2->DATA &= ~(1<<led);		// P2.1
}

