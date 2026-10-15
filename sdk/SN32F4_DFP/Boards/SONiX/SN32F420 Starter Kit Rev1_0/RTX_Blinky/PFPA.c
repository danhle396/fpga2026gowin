/******************** (C) COPYRIGHT 2026 SONiX *******************************
* COMPANY:			SONiX
* DATE:					2026/04
* AUTHOR:				SA1
* IC:						SN32F420
* DESCRIPTION:	PFPA related functions.
*____________________________________________________________________________
*	REVISION	Date				User		Description
*	1.0				2026/04/09	SA1			1. First version release
*
*____________________________________________________________________________
* THE PRESENT SOFTWARE WHICH IS FOR GUIDANCE ONLY AIMS AT PROVIDING CUSTOMERS
* WITH CODING INFORMATION REGARDING THEIR PRODUCTS TIME TO MARKET.
* SONiX SHALL NOT BE HELD LIABLE FOR ANY DIRECT, INDIRECT OR CONSEQUENTIAL 
* DAMAGES WITH RESPECT TO ANY CLAIMS ARISING FROM THE CONTENT OF SUCH SOFTWARE
* AND/OR THE USE MADE BY CUSTOMERS OF THE CODING INFORMATION CONTAINED HEREIN 
* IN CONNECTION WITH THEIR PRODUCTS.
*****************************************************************************/


/*_____ I N C L U D E S ____________________________________________________*/
#include <SN32F420.h>



/*
//-------- <<< Use Configuration Wizard in Context Menu >>> ------------------
*/

//--------------------- Clock Configuration ----------------------------------
//
//<e> UART0
#define UART0_EN		0
//		<o.2..3> URXD0=
//					<0=> P1.0
//					<1=> P2.0
//					<2=> P1.6
//					<3=> P0.6
//		<o.0..1> UTXD0=
//					<0=> P1.1
//					<1=> P2.1
//					<2=> P1.7
//					<3=> P0.7
//</e>
#define PFPA_UART0_VAL								0x00000000
//<e> UART1
#define UART1_EN		0
//		<o.2..3> URXD1=
//					<0=> P1.2
//					<1=> P3.8
//					<2=> P3.4
//					<3=> P0.4
//		<o.0..1> UTXD1=
//					<0=> P1.3
//					<1=> P3.9
//					<2=> P3.5
//					<3=> P0.5
//</e>
#define PFPA_UART1_VAL								0x00000000
//<e> SPI0
#define SPI0_EN		0
//		<o.4..5> SCK0=
//					<0=> P1.0
//					<1=> P3.8
//					<2=> P0.2
//					<3=> P2.1
//		<o.6..7> SEL0=
//					<0=> P1.1
//					<1=> P3.7
//					<2=> P0.3
//					<3=> P2.2
//		<o.0..1> MISO0=
//					<0=> P1.2
//					<1=> P3.5
//					<2=> P0.4
//					<3=> P2.3
//		<o.2..3> MOSI0=
//					<0=> P1.3
//					<1=> P3.4
//					<2=> P0.5
//					<3=> P2.4
//</e>
#define PFPA_SPI0_VAL								0x00000000
//<e> I2C0
#define I2C0_EN		0
//		<o.2..3> SCL0=
//					<0=> P1.0
//					<1=> P1.2
//					<2=> P3.4
//					<3=> P3.8
//		<o.0..1> SDA0=
//					<0=> P1.1
//					<1=> P1.3
//					<2=> P3.5
//					<3=> P3.9
//</e>
#define PFPA_I2C0_VAL								0x00000000
//<e> MT16B0
#define MT16B0_EN		0
//		<o.0..1> PWM0=
//					<0=> P0.2
//					<1=> P1.7
//					<2=> P1.0
//					<3=> P2.4
//		<o.2..3> PWM0N=
//					<0=> P0.3
//					<1=> P0.5
//					<2=> P1.1
//					<3=> P1.3
//		<o.4..5> PWM1=
//					<0=> P0.4
//					<1=> P0.3
//					<2=> P1.2
//					<3=> P1.1
//		<o.6..7> PWM1N=
//					<0=> P0.5
//					<1=> P0.6
//					<2=> P1.3
//					<3=> P1.4
//		<o.8..9> PWM2=
//					<0=> P0.6
//					<1=> P0.4
//					<2=> P1.4
//					<3=> P1.2
//		<o.10..11> PWM2N=
//					<0=> P0.7
//					<1=> P3.4
//					<2=> P1.6
//					<3=> P1.7
//		<o.12..13> PWM3=
//					<0=> P3.4
//					<1=> P3.7
//					<2=> P1.7
//					<3=> P2.3
//		<o.14..15> PWM3N=
//					<0=> P3.5
//					<1=> P3.8
//					<2=> P0.2
//					<3=> P2.4
//		<o.30..31> BRK=
//					<0=> P1.4
//					<1=> P3.5
//					<2=> P3.7
//					<3=> P1.0
//</e>
#define PFPA_MT16B0_VAL								0x00000000
//<e> UT16B0
#define UT16B0_EN		0
//		<o.0..1> PWM0=
//					<0=> P2.0
//					<1=> P1.2
//					<2=> P1.0
//					<3=> P0.6
//		<o.2..3> PWM1=
//					<0=> P2.1
//					<1=> P1.3
//					<2=> P1.1
//					<3=> P0.7
//</e>
#define PFPA_UT16B0_VAL								0x00000000
//<e> UT16B1
#define UT16B1_EN		0
//		<o.0..1> PWM0=
//					<0=> P0.4
//					<1=> P3.8
//					<2=> P2.2
//					<3=> P3.6
//		<o.2..3> PWM1=
//					<0=> P0.5
//					<1=> P3.9
//					<2=> P2.3
//					<3=> P3.7
//</e>
#define PFPA_UT16B1_VAL								0x00000000
//<e> HALL
#define HALL_EN		0
//		<o.0> IN0=
//					<0=> P3.7
//					<1=> P1.2
//		<o.1> IN1=
//					<0=> P3.8
//					<1=> P1.3
//		<o.2> IN2=
//					<0=> P3.9
//					<1=> P1.4
//</e>
#define PFPA_HALL_VAL								0x00000000
/*
//-------- <<< end of configuration section >>> ------------------------------
*/

/*_____ D E C L A R A T I O N S ____________________________________________*/

const uint32_t      BL_PFPA_UTXD0		__attribute__((at(0x000000e0))) = (PFPA_UART0_VAL & 0x3);			//PFPA No of UTXD0 for Boot loader 
const uint32_t      BL_PFPA_URXD0		__attribute__((at(0x000000f0))) = (PFPA_UART0_VAL>>2) & 0x3;		//PFPA No of URXD0 for Boot loader  



/*_____ F U N C T I O N S __________________________________________________*/
void PFPA_Init (void)
{
	SN_PFPA->UART0  = PFPA_UART0_VAL;
	SN_PFPA->UART1  = PFPA_UART1_VAL;
	SN_PFPA->SPI0   = PFPA_SPI0_VAL;
	SN_PFPA->I2C0   = PFPA_I2C0_VAL;
	SN_PFPA->MT16B0 = PFPA_MT16B0_VAL;
	SN_PFPA->UT16B0 = PFPA_UT16B0_VAL;
	SN_PFPA->UT16B1 = PFPA_UT16B1_VAL;
	SN_PFPA->HALL    = PFPA_HALL_VAL;
}
