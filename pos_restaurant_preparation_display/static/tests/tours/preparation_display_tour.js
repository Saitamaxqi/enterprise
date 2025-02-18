import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as ProductScreenPos from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
import * as PrepDisplay from "@pos_restaurant_preparation_display/../tests/tours/utils/preparation_display_util";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto, ...PrepDisplay };
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PreparationDisplayTourResto", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Create first order
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.orderlineIsToOrder("Water"),
            ProductScreen.orderlineIsToOrder("Coca-Cola"),
            ProductScreen.clickOrderButton(),
            FloorScreen.clickTable("5"),
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),

            // Create second order
            FloorScreen.isShown(),
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.orderlineIsToOrder("Coca-Cola"),
            ProductScreen.clickOrderButton(),
            FloorScreen.clickTable("4"),
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),

            // Create third order
            FloorScreen.isShown(),
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.clickDisplayedProduct("Minute Maid"),
            ProductScreen.orderlineIsToOrder("Coca-Cola"),
            ProductScreen.orderlineIsToOrder("Water"),
            ProductScreen.orderlineIsToOrder("Minute Maid"),
            ProductScreen.clickOrderButton(),
            FloorScreen.clickTable("4"),
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.clickOrderline("Minute Maid"),
            ProductScreen.selectedOrderlineHas("Minute Maid", "1"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Minute Maid", "0"),
            ProductScreen.orderlineIsToOrder("Minute Maid"),
            ProductScreen.clickOrderButton(),
            FloorScreen.clickTable("4"),
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("PreparationDisplayTourInternalNotes", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.addInternalNote("Test Internal Notes", "Note"),
            ProductScreen.orderlineIsToOrder("Coca-Cola"),
            ProductScreen.clickOrderButton(),
            Chrome.waitRequest(),
            FloorScreen.clickTable("5"),
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickOrderButton(),
            Chrome.waitRequest(),
            FloorScreen.clickTable("5"),
            ProductScreen.orderlinesHaveNoChange(),
            Order.hasLine({
                productName: "Coca-Cola",
                internalNote: "Test Internal Notes",
            }),
            Order.hasLine({
                productName: "Coca-Cola",
                internalNote: "",
            }),
            Chrome.clickPlanButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("PreparationDisplayTourResto2", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Create first order
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.orderlineIsToOrder("Coca-Cola"),
            ProductScreen.clickOrderButton(),
            FloorScreen.clickTable("5"),
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.orderlineIsToOrder("Coca-Cola"),
            ProductScreen.clickOrderButton(),
            FloorScreen.clickTable("5"),
            ProductScreen.orderlinesHaveNoChange(),
            Chrome.clickPlanButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("PreparationDisplayCancelOrderTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Test Food"),
            ProductScreen.orderlineIsToOrder("Test Food"),
            ProductScreen.clickOrderButton(),
            FloorScreen.clickTable("5"),
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.clickReview(),
            ProductScreen.clickControlButton("Cancel Order"),
            Dialog.confirm(),
            FloorScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("PreparationDisplayPaymentNotCancelDisplayTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.addOrderline("Coca-Cola", "2"),
            ProductScreen.addInternalNote("To Serve"),
            ProductScreen.clickOrderButton(),
            FloorScreen.clickTable("5"),
            ProductScreen.addOrderline("Coca-Cola", "2"),
            ProductScreen.addInternalNote("To Serve"),
            ProductScreen.clickOrderButton(),
            FloorScreen.clickTable("5"),
            ProductScreen.clickOrderline("Coca-Cola", "2"),
            ProductScreen.clickNumpad("1"),
            ProductScreen.clickOrderButton(),
            FloorScreen.clickTable("5"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            Chrome.endTour(),
        ].flat(),
});

function clickOrderButton() {
    return [
        ProductScreen.clickOrderButton(),
        {
            trigger: ".oe_status .fa.fa-spin",
        },
        Chrome.isSynced(),
        ProductScreen.orderlinesHaveNoChange(),
    ].flat();
}

registry.category("web_tour.tours").add("test_update_internal_note_of_order", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickSubcategory("Test-cat"),
            ProductScreen.clickDisplayedProduct("Demo Food"),
            ProductScreen.clickDisplayedProduct("Test Food"),
            ProductScreen.orderlineIsToOrder("Test Food"),
            clickOrderButton(),
            FloorScreen.clickTable("5"),
            ProductScreen.clickOrderline("Test Food"),
            ProductScreen.addInternalNote("Test Internal Notes"),
            ProductScreen.selectedOrderlineHas("Test Food", "1.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Test Food", "0.0"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Demo Food", "1.0"),
            clickOrderButton(),
            FloorScreen.clickTable("5"),
            ProductScreen.totalAmountIs("10"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});
